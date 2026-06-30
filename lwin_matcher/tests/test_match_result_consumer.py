from __future__ import annotations

import queue
import threading

from app.service.pipeline.match_result_consumer import MatchResultConsumer


class FakeLwinClient:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def bulk_upsert(self, rows, conflict_columns):
        self.rows.extend(rows)
        return len(rows)


class FakeCheckpointManager:
    def __init__(self) -> None:
        self.saved: list[int] = []

    def save(self, checkpoint_id: int) -> None:
        self.saved.append(checkpoint_id)


def _result(lot_item_id: int) -> dict:
    return {
        "lot_item_id": lot_item_id,
        "checkpoint_id": lot_item_id,
        "matched": "exact_match",
        "lwin_codes": [1234567],
        "lwin_11_codes": [12345672018],
        "match_items": [{"display_name": "Wine"}],
        "match_scores": [0.95],
    }


def test_checkpoint_is_saved_once_after_all_results_are_flushed() -> None:
    result_queue: queue.Queue = queue.Queue()
    result_queue.put(_result(20))
    result_queue.put(_result(10))
    result_queue.put(_result(30))
    result_queue.put(None)

    lwin_client = FakeLwinClient()
    checkpoint_manager = FakeCheckpointManager()

    stats = MatchResultConsumer(
        lwin_client=lwin_client,
        checkpoint_manager=checkpoint_manager,
        flush_size=2,
        result_queue=result_queue,
        worker_count=1,
        shutdown_event=threading.Event(),
    ).run()

    assert stats.total_upserted == 3
    assert checkpoint_manager.saved == [30]
