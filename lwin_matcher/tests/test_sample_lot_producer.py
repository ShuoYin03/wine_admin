from __future__ import annotations

import queue
import threading
from unittest.mock import MagicMock

from app.service.pipeline.sample_lot_producer import SampleLotProducer


def _make_lot(offset: int) -> dict:
    return {
        "lot_name": f"Chateau Wine {offset}",
        "external_id": f"EXT-{offset}",
        "region": "Bordeaux",
        "sub_region": None,
        "country": "France",
        "lot_items": [
            {
                "id": offset * 100 + 1,
                "lot_producer": "Chateau X",
                "vintage": 2018,
                "colour": "Red",
            }
        ],
    }


def _make_lots_client(total: int) -> MagicMock:
    mock = MagicMock()

    def query_side_effect(**kwargs):
        if kwargs.get("return_count"):
            return ([], total)
        offset = kwargs.get("offset", 0)
        return ([_make_lot(offset)], None)

    mock.query_lots_with_items_and_auction.side_effect = query_side_effect
    return mock


def _drain_queue(work_queue: queue.Queue) -> tuple[list[dict], int]:
    """Returns (non_sentinel_items, sentinel_count)."""
    items: list[dict] = []
    sentinels = 0
    while not work_queue.empty():
        item = work_queue.get_nowait()
        if item is None:
            sentinels += 1
        else:
            items.append(item)
    return items, sentinels


class TestSampleLotProducer:
    def test_produces_correct_number_of_items(self) -> None:
        lots_client = _make_lots_client(50)
        work_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        producer = SampleLotProducer(
            lots_client=lots_client,
            filters=[],
            auction_house=None,
            sample_size=10,
            seed=42,
            work_queue=work_queue,
            worker_count=2,
            shutdown_event=shutdown_event,
        )

        total = producer.run()

        assert total == 10
        items, sentinels = _drain_queue(work_queue)
        assert len(items) == 10
        assert sentinels == 2

    def test_clips_sample_size_to_total_lots(self) -> None:
        lots_client = _make_lots_client(5)
        work_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        producer = SampleLotProducer(
            lots_client=lots_client,
            filters=[],
            auction_house=None,
            sample_size=100,  # more than total
            seed=42,
            work_queue=work_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        )

        total = producer.run()

        assert total == 5
        items, sentinels = _drain_queue(work_queue)
        assert len(items) == 5
        assert sentinels == 1

    def test_work_item_has_required_fields(self) -> None:
        lots_client = _make_lots_client(20)
        work_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        producer = SampleLotProducer(
            lots_client=lots_client,
            filters=[],
            auction_house=None,
            sample_size=3,
            seed=42,
            work_queue=work_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        )

        producer.run()
        items, _ = _drain_queue(work_queue)

        assert len(items) == 3
        for item in items:
            assert "lot_item_id" in item
            assert "lot_offset" in item
            assert "wine_name" in item
            assert "lot_producer" in item
            assert "lot_external_id" in item
            assert item["lot_offset"] == 0  # sample mode always uses offset=0

    def test_empty_db_produces_only_sentinels(self) -> None:
        mock = MagicMock()
        mock.query_lots_with_items_and_auction.return_value = ([], 0)
        work_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        producer = SampleLotProducer(
            lots_client=mock,
            filters=[],
            auction_house=None,
            sample_size=10,
            seed=42,
            work_queue=work_queue,
            worker_count=3,
            shutdown_event=shutdown_event,
        )

        total = producer.run()

        assert total == 0
        items, sentinels = _drain_queue(work_queue)
        assert len(items) == 0
        assert sentinels == 3

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed must produce the same offset selection."""
        lots_client = _make_lots_client(100)
        recorded_offsets: list[list[int]] = []

        for _ in range(2):
            work_queue: queue.Queue = queue.Queue()
            shutdown_event = threading.Event()
            producer = SampleLotProducer(
                lots_client=lots_client,
                filters=[],
                auction_house=None,
                sample_size=5,
                seed=99,
                work_queue=work_queue,
                worker_count=1,
                shutdown_event=shutdown_event,
            )
            producer.run()
            items, _ = _drain_queue(work_queue)
            recorded_offsets.append([i["lot_item_id"] for i in items])

        assert recorded_offsets[0] == recorded_offsets[1]
