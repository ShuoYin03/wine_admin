from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import Any

from .checkpoint_manager import CheckpointManager
from .utils import clean_nan


@dataclass
class ConsumerStats:
    total_upserted: int = 0
    total_failed: int = 0


class MatchResultConsumer:
    """
    Drains the result_queue, batches results up to flush_size, then
    bulk_upserts to DB and writes a checkpoint.

    Terminates after receiving one sentinel (None) per worker thread.
    Runs in a single dedicated thread.
    """

    def __init__(
        self,
        lwin_client: Any,
        checkpoint_manager: CheckpointManager,
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
        min_offset: int | None = None
        sentinels_received = 0

        while True:
            try:
                result = self._result_queue.get(timeout=1.0)
            except queue.Empty:
                # No results yet — flush buffer if shutdown signalled externally
                if self._shutdown_event.is_set() and buffer:
                    self._flush(buffer, min_offset, stats)
                    buffer = []
                    min_offset = None
                continue

            if result is None:
                sentinels_received += 1
                if sentinels_received >= self._worker_count:
                    # All workers done — final flush
                    if buffer:
                        self._flush(buffer, min_offset, stats)
                    break
                continue

            if result.get("error"):
                stats.total_failed += 1
                continue

            lot_offset: int = result.get("lot_offset", 0)
            if min_offset is None or lot_offset < min_offset:
                min_offset = lot_offset

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
                self._flush(buffer, min_offset, stats)
                buffer = []
                min_offset = None

        print(
            f"[Consumer] Done. Upserted: {stats.total_upserted}, "
            f"Failed: {stats.total_failed}"
        )
        return stats

    def _flush(self, buffer: list[dict], lot_offset: int | None, stats: ConsumerStats) -> None:
        try:
            upserted = self._lwin_client.bulk_upsert(
                buffer, conflict_columns=["lot_item_id"]
            )
            stats.total_upserted += upserted
            if lot_offset is not None:
                self._checkpoint_manager.save(lot_offset)
            print(
                f"[Consumer] Flushed {len(buffer)} rows "
                f"(checkpoint offset={lot_offset}, total={stats.total_upserted})"
            )
        except Exception as e:
            first_line = str(e).split("\n")[0][:300]
            print(f"[Consumer] Flush error ({type(e).__name__}): {first_line}")
            stats.total_failed += len(buffer)


