from __future__ import annotations

import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.models.lwin_matching_params import LwinMatchingParams

from .checkpoint_manager import CheckpointManager
from .config import LOT_TYPE_FILTERS, PipelineConfig
from .csv_match_result_consumer import CsvMatchResultConsumer, CsvStats
from .lot_item_producer import LotItemProducer
from .match_result_consumer import ConsumerStats, MatchResultConsumer
from .sample_lot_producer import SampleLotProducer


@dataclass
class PipelineResult:
    processed: int
    upserted: int
    failed: int
    duration_seconds: float


class LwinMatchingPipeline:
    def __init__(
        self,
        config: PipelineConfig,
        engine: Any,
        lots_client: Any,
        lwin_client: Any,
    ) -> None:
        self._config = config
        self._engine = engine
        self._lots_client = lots_client
        self._lwin_client = lwin_client
        checkpoint_kind = "missing_items" if config.only_missing else "all_items"
        self._checkpoint_manager = CheckpointManager(
            config.auction_house,
            checkpoint_kind=checkpoint_kind,
        )

    def run(self) -> PipelineResult:
        start_time = time.monotonic()
        cfg = self._config

        work_queue: queue.Queue = queue.Queue(maxsize=cfg.work_queue_maxsize)
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        is_sample = cfg.output_csv is not None

        if is_sample:
            producer: Any = SampleLotProducer(
                lots_client=self._lots_client,
                filters=LOT_TYPE_FILTERS,
                auction_house=cfg.auction_house,
                sample_size=cfg.sample_size or 100,
                seed=cfg.sample_seed,
                work_queue=work_queue,
                worker_count=cfg.worker_count,
                shutdown_event=shutdown_event,
            )
            consumer: Any = CsvMatchResultConsumer(
                output_csv=cfg.output_csv,
                result_queue=result_queue,
                worker_count=cfg.worker_count,
                shutdown_event=shutdown_event,
            )
        else:
            start_after_id = 0 if cfg.only_missing else self._resolve_start_checkpoint(cfg)
            producer = LotItemProducer(
                lots_client=self._lots_client,
                filters=LOT_TYPE_FILTERS,
                auction_house=cfg.auction_house,
                fetch_batch_size=cfg.fetch_batch_size,
                start_after_id=start_after_id,
                only_missing=cfg.only_missing,
                work_queue=work_queue,
                worker_count=cfg.worker_count,
                shutdown_event=shutdown_event,
            )
            consumer = MatchResultConsumer(
                lwin_client=self._lwin_client,
                checkpoint_manager=None if cfg.only_missing else self._checkpoint_manager,
                flush_size=cfg.flush_size,
                result_queue=result_queue,
                worker_count=cfg.worker_count,
                shutdown_event=shutdown_event,
            )

        # --- Launch producer and consumer threads ---
        producer_thread = threading.Thread(
            target=producer.run, name="lwin-producer", daemon=False
        )
        consumer_result: list[Any] = []

        def _consumer_runner() -> None:
            consumer_result.append(consumer.run())

        consumer_thread = threading.Thread(
            target=_consumer_runner, name="lwin-consumer", daemon=False
        )

        # --- Worker loop (runs inside ThreadPoolExecutor threads) ---
        def _worker_loop() -> None:
            try:
                while True:
                    item = work_queue.get()
                    if item is None:
                        break
                    try:
                        result = self.process_item(item)
                        result_queue.put(result)
                    except Exception as e:
                        lot_item_id = item.get("lot_item_id")
                        print(f"[Worker] Error lot_item_id={lot_item_id}: {e}")
                        result_queue.put({"error": True, "lot_item_id": lot_item_id})
            finally:
                # Always send sentinel so consumer can count worker exits
                result_queue.put(None)

        # --- Start everything ---
        producer_thread.start()
        consumer_thread.start()

        with ThreadPoolExecutor(
            max_workers=cfg.worker_count, thread_name_prefix="lwin-worker"
        ) as executor:
            futures = [executor.submit(_worker_loop) for _ in range(cfg.worker_count)]
            for f in futures:
                f.result()  # Propagates any unexpected worker exception

        producer_thread.join()
        consumer_thread.join()

        stats: ConsumerStats | CsvStats = (
            consumer_result[0] if consumer_result
            else (CsvStats() if is_sample else ConsumerStats())
        )
        duration = time.monotonic() - start_time

        print(
            f"\n[Pipeline] Finished — "
            f"upserted={stats.total_upserted}, "
            f"failed={stats.total_failed}, "
            f"duration={duration:.1f}s"
        )
        return PipelineResult(
            processed=stats.total_upserted + stats.total_failed,
            upserted=stats.total_upserted,
            failed=stats.total_failed,
            duration_seconds=duration,
        )

    def _resolve_start_checkpoint(self, cfg: PipelineConfig) -> int:
        if not cfg.resume:
            self._checkpoint_manager.clear()
            print("[Pipeline] --no-resume: cleared checkpoint, starting from lot_item_id 0.")
            return 0

        last = self._checkpoint_manager.load()
        if last >= 0:
            print(f"[Pipeline] Resuming after lot_item_id {last}.")
            return last

        print("[Pipeline] No checkpoint found, starting from lot_item_id 0.")
        return 0

    def process_item(self, item: dict) -> dict:
        params = LwinMatchingParams(
            wine_name=item.get("wine_name") or "",
            lot_producer=item.get("lot_producer") or "",
            vintage=item.get("vintage"),
            region=item.get("region"),
            sub_region=item.get("sub_region"),
            country=item.get("country"),
            colour=item.get("colour"),
        )

        match_result, lwin_codes, scores, match_items = self._engine.match(params)

        vintage = item.get("vintage")
        lwin_11_codes: list[int] | None = None
        vintage_str = str(vintage) if vintage is not None else ""
        if lwin_codes and len(vintage_str) == 4:
            lwin_11_codes = [int(str(code) + vintage_str) for code in lwin_codes]

        return {
            "lot_item_id": item["lot_item_id"],
            "checkpoint_id": item.get(
                "checkpoint_id",
                item.get("lot_offset", item["lot_item_id"]),
            ),
            "lot_offset": item.get("lot_offset", item["lot_item_id"]),
            "matched": match_result.value,
            "lwin_codes": lwin_codes,
            "lwin_11_codes": lwin_11_codes,
            "match_scores": scores,
            "match_items": list(match_items),
            "wine_name": item.get("wine_name"),
            "lot_producer": item.get("lot_producer"),
            "vintage": item.get("vintage"),
            "region": item.get("region"),
            "sub_region": item.get("sub_region"),
            "country": item.get("country"),
            "colour": item.get("colour"),
            "lot_external_id": item.get("lot_external_id"),
        }
