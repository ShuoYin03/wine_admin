from __future__ import annotations

import csv
import os
import queue
import threading
from dataclasses import dataclass

from .utils import clean_nan

CSV_FIELD_ORDER: list[str] = [
    "lot_external_id",
    "lot_name",
    "region",
    "sub_region",
    "country",
    "lot_item_id",
    "lot_producer",
    "vintage",
    "colour",
    "matched",
    "lwin_code",
    "lwin_11_code",
    "match_score",
    "matched_ref_id",
    "matched_lwin",
    "matched_reference",
    "matched_display_name",
    "matched_producer_name",
    "matched_wine",
    "matched_colour",
    "matched_region",
    "matched_sub_region",
    "matched_country",
    "matched_classification",
]


@dataclass
class CsvStats:
    # Named total_upserted for PipelineResult compatibility; value = rows written to CSV
    total_upserted: int = 0
    total_failed: int = 0


class CsvMatchResultConsumer:
    """
    Drains result_queue, assembles a CSV row per result using both match data and
    passthrough context fields (wine_name, region, etc.) populated by process_item,
    then writes all rows to output_csv when all workers are done.

    Terminates after receiving one sentinel (None) per worker thread.
    Runs in a single dedicated thread.
    """

    def __init__(
        self,
        output_csv: str,
        result_queue: queue.Queue,
        worker_count: int,
        shutdown_event: threading.Event,
    ) -> None:
        self._output_csv = output_csv
        self._result_queue = result_queue
        self._worker_count = worker_count
        self._shutdown_event = shutdown_event

    def run(self) -> CsvStats:
        stats = CsvStats()
        rows: list[dict] = []
        sentinels_received = 0

        while True:
            try:
                result = self._result_queue.get(timeout=1.0)
            except queue.Empty:
                if self._shutdown_event.is_set():
                    break
                continue

            if result is None:
                sentinels_received += 1
                if sentinels_received >= self._worker_count:
                    break
                continue

            if result.get("error"):
                stats.total_failed += 1
                continue

            top: dict = (result.get("match_items") or [{}])[0]
            lwin_codes: list = result.get("lwin_codes") or []
            lwin_11_codes: list = result.get("lwin_11_codes") or []
            scores: list = result.get("match_scores") or []

            rows.append(clean_nan({
                "lot_external_id": result.get("lot_external_id"),
                "lot_name": result.get("wine_name"),
                "region": result.get("region"),
                "sub_region": result.get("sub_region"),
                "country": result.get("country"),
                "lot_item_id": result.get("lot_item_id"),
                "lot_producer": result.get("lot_producer"),
                "vintage": result.get("vintage"),
                "colour": result.get("colour"),
                "matched": result.get("matched"),
                "lwin_code": lwin_codes[0] if lwin_codes else None,
                "lwin_11_code": lwin_11_codes[0] if lwin_11_codes else None,
                "match_score": scores[0] if scores else None,
                "matched_ref_id": top.get("id"),
                "matched_lwin": top.get("lwin"),
                "matched_reference": top.get("reference"),
                "matched_display_name": top.get("display_name"),
                "matched_producer_name": top.get("producer_name"),
                "matched_wine": top.get("wine"),
                "matched_colour": top.get("colour"),
                "matched_region": top.get("region"),
                "matched_sub_region": top.get("sub_region"),
                "matched_country": top.get("country"),
                "matched_classification": top.get("classification"),
            }))
            stats.total_upserted += 1

        os.makedirs(os.path.dirname(os.path.abspath(self._output_csv)), exist_ok=True)
        with open(self._output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELD_ORDER, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(
            f"[CsvConsumer] Done. Written: {stats.total_upserted}, "
            f"Failed: {stats.total_failed} → {self._output_csv}"
        )
        return stats
