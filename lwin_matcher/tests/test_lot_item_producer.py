from __future__ import annotations

import queue
import threading

from app.service.pipeline.lot_item_producer import LotItemProducer


def _row(lot_item_id: int) -> dict:
    return {
        "lot_item_id": lot_item_id,
        "wine_name": f"Wine {lot_item_id}",
        "lot_producer": "Producer",
        "vintage": "2018",
        "region": "Bordeaux",
        "sub_region": None,
        "country": "France",
        "colour": "Red",
        "lot_external_id": f"LOT-{lot_item_id}",
    }


class FakeLotsClient:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def query_lot_items_for_lwin_matching(self, **kwargs):
        self.calls.append(kwargs)
        remaining = [
            row for row in self.rows
            if row["lot_item_id"] > kwargs.get("last_lot_item_id", 0)
        ]
        if kwargs.get("return_count"):
            return ([], len(remaining))
        return (remaining[: kwargs["limit"]], None)


def _drain(work_queue: queue.Queue) -> tuple[list[dict], int]:
    items: list[dict] = []
    sentinels = 0
    while not work_queue.empty():
        item = work_queue.get_nowait()
        if item is None:
            sentinels += 1
        else:
            items.append(item)
    return items, sentinels


class TestLotItemProducer:
    def test_produces_items_with_keyset_cursor(self) -> None:
        lots_client = FakeLotsClient([_row(10), _row(20), _row(35)])
        work_queue: queue.Queue = queue.Queue()

        total = LotItemProducer(
            lots_client=lots_client,
            filters=[],
            auction_house=None,
            fetch_batch_size=2,
            start_after_id=0,
            only_missing=False,
            work_queue=work_queue,
            worker_count=2,
            shutdown_event=threading.Event(),
        ).run()

        items, sentinels = _drain(work_queue)

        assert total == 3
        assert [item["lot_item_id"] for item in items] == [10, 20, 35]
        assert [item["checkpoint_id"] for item in items] == [10, 20, 35]
        assert sentinels == 2
        data_calls = [
            call for call in lots_client.calls
            if not call.get("return_count")
        ]
        assert [call["last_lot_item_id"] for call in data_calls] == [0, 20, 35]

    def test_passes_only_missing_to_query(self) -> None:
        lots_client = FakeLotsClient([_row(1)])
        work_queue: queue.Queue = queue.Queue()

        LotItemProducer(
            lots_client=lots_client,
            filters=[],
            auction_house="Zachys",
            fetch_batch_size=10,
            start_after_id=100,
            only_missing=True,
            work_queue=work_queue,
            worker_count=1,
            shutdown_event=threading.Event(),
        ).run()

        assert all(call["only_missing"] is True for call in lots_client.calls)
        assert all(call["auction_house"] == "Zachys" for call in lots_client.calls)
