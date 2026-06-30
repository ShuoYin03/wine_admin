from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Any

from .checkpoint_manager import CheckpointManager
from .utils import clean_nan


@dataclass
class ConsumerStats:
    total_upserted: int = 0
    total_failed: int = 0


class MatchResultConsumer:
    """
    Drains the result queue, bulk-upserts match rows, and writes a checkpoint
    only after all workers have completed successfully.
    """

    def __init__(
        self,
        lwin_client: Any,
        checkpoint_manager: CheckpointManager | None,
        flush_size: int,
        result_queue: queue.Queue,
        worker_count: int,
        shutdown_event: threading.Event,
    ) -> None:
        self._lwin_client = lwin_client
        self._checkpoint_manager = checkpoint_manager
        self._flush_size = flush_size
        self._result_queue = result_queue
        self._worker_count = worker_count
        self._shutdown_event = shutdown_event

    def run(self) -> ConsumerStats:
        stats = ConsumerStats()
        buffer: list[dict] = []
        max_checkpoint_id: int | None = None
        sentinels_received = 0

        while True:
            try:
                result = self._result_queue.get(timeout=1.0)
            except queue.Empty:
                if self._shutdown_event.is_set() and buffer:
                    self._flush(buffer, stats)
                    buffer = []
                continue

            if result is None:
                sentinels_received += 1
                if sentinels_received >= self._worker_count:
                    if buffer:
                        self._flush(buffer, stats)
                    break
                continue

            if result.get("error"):
                stats.total_failed += 1
                continue

            checkpoint_id = result.get("checkpoint_id", result.get("lot_offset"))
            if checkpoint_id is not None:
                checkpoint_id = int(checkpoint_id)
                if max_checkpoint_id is None or checkpoint_id > max_checkpoint_id:
                    max_checkpoint_id = checkpoint_id

            data_dict = clean_nan({
                "lot_item_id": result["lot_item_id"],
                "matched": result.get("matched"),
                "lwin": result.get("lwin_codes"),
                "lwin_11": result.get("lwin_11_codes"),
                "match_item": result.get("match_items"),
                "match_score": result.get("match_scores"),
            })
            buffer.append(data_dict)

            if len(buffer) >= self._flush_size:
                self._flush(buffer, stats)
                buffer = []

        if (
            self._checkpoint_manager is not None
            and max_checkpoint_id is not None
            and stats.total_failed == 0
        ):
            self._checkpoint_manager.save(max_checkpoint_id)
            print(f"[Consumer] Checkpoint saved at lot_item_id={max_checkpoint_id}")

        print(
            f"[Consumer] Done. Upserted: {stats.total_upserted}, "
            f"Failed: {stats.total_failed}"
        )
        return stats

    def _flush(self, buffer: list[dict], stats: ConsumerStats) -> None:
        try:
            upserted = self._lwin_client.bulk_upsert(
                buffer, conflict_columns=["lot_item_id"]
            )
            stats.total_upserted += upserted
            print(
                f"[Consumer] Flushed {len(buffer)} rows "
                f"(total={stats.total_upserted})"
            )
        except Exception as e:
            first_line = str(e).split("\n")[0][:300]
            print(f"[Consumer] Flush error ({type(e).__name__}): {first_line}")
            stats.total_failed += len(buffer)
