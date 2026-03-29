from __future__ import annotations

import csv as csv_mod
import os
import queue
import threading

from app.service.pipeline.csv_match_result_consumer import (
    CSV_FIELD_ORDER,
    CsvMatchResultConsumer,
    CsvStats,
)


def _make_result(lot_item_id: int, matched: str = "exact_match") -> dict:
    return {
        "lot_item_id": lot_item_id,
        "lot_offset": 0,
        "matched": matched,
        "lwin_codes": [1234567],
        "lwin_11_codes": [12345672018],
        "match_scores": [0.95],
        "match_items": [
            {
                "id": 1,
                "lwin": 1234567,
                "reference": None,
                "display_name": "Wine A",
                "producer_name": "Prod",
                "wine": "Wine A",
                "colour": "Red",
                "region": "Bordeaux",
                "sub_region": None,
                "country": "France",
                "classification": None,
            }
        ],
        "wine_name": f"Wine {lot_item_id}",
        "lot_producer": "Prod",
        "vintage": 2018,
        "region": "Bordeaux",
        "sub_region": None,
        "country": "France",
        "colour": "Red",
        "lot_external_id": f"EXT-{lot_item_id}",
    }


class TestCsvMatchResultConsumer:
    def test_writes_csv_rows(self, tmp_path) -> None:
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        result_queue.put(_make_result(1))
        result_queue.put(_make_result(2))
        result_queue.put(None)  # single sentinel (worker_count=1)

        consumer = CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        )
        stats = consumer.run()

        assert stats.total_upserted == 2
        assert stats.total_failed == 0
        assert os.path.exists(output)

        with open(output, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["lot_external_id"] == "EXT-1"
        assert rows[0]["matched"] == "exact_match"
        assert rows[1]["lot_external_id"] == "EXT-2"

    def test_error_results_counted_but_not_written(self, tmp_path) -> None:
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        result_queue.put(_make_result(1))
        result_queue.put({"error": True, "lot_item_id": 2})
        result_queue.put(None)

        consumer = CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        )
        stats = consumer.run()

        assert stats.total_upserted == 1
        assert stats.total_failed == 1

        with open(output, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        assert len(rows) == 1

    def test_waits_for_all_worker_sentinels(self, tmp_path) -> None:
        """Consumer must collect both sentinels before writing CSV."""
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        # Results and sentinels interleaved across two workers
        result_queue.put(_make_result(1))
        result_queue.put(None)  # sentinel from worker 1
        result_queue.put(_make_result(2))
        result_queue.put(None)  # sentinel from worker 2

        consumer = CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=2,
            shutdown_event=shutdown_event,
        )
        stats = consumer.run()

        assert stats.total_upserted == 2
        assert stats.total_failed == 0

        with open(output, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        assert len(rows) == 2

    def test_empty_results_produce_empty_csv(self, tmp_path) -> None:
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        result_queue.put(None)  # single sentinel

        consumer = CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        )
        stats = consumer.run()

        assert stats.total_upserted == 0
        assert stats.total_failed == 0
        assert os.path.exists(output)

        with open(output, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        assert len(rows) == 0

    def test_csv_has_correct_header_columns(self, tmp_path) -> None:
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        result_queue.put(_make_result(1))
        result_queue.put(None)

        CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        ).run()

        with open(output, newline="", encoding="utf-8") as f:
            reader = csv_mod.DictReader(f)
            assert list(reader.fieldnames or []) == CSV_FIELD_ORDER

    def test_lot_name_mapped_from_wine_name(self, tmp_path) -> None:
        """wine_name passthrough field is written to the lot_name CSV column."""
        output = str(tmp_path / "out.csv")
        result_queue: queue.Queue = queue.Queue()
        shutdown_event = threading.Event()

        result = _make_result(1)
        result["wine_name"] = "Petrus 2015"
        result_queue.put(result)
        result_queue.put(None)

        CsvMatchResultConsumer(
            output_csv=output,
            result_queue=result_queue,
            worker_count=1,
            shutdown_event=shutdown_event,
        ).run()

        with open(output, newline="", encoding="utf-8") as f:
            rows = list(csv_mod.DictReader(f))
        assert rows[0]["lot_name"] == "Petrus 2015"
