from __future__ import annotations

import queue
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

_SENTINEL = None  # Signals workers to stop


class SampleLotProducer:
    """
    Fetches a random sample of lots from DB using concurrent individual offset queries,
    then places each lot_item as a work unit onto the work_queue.

    Interface-compatible with LotProducer: same work item format and sentinel logic.
    Runs in a single dedicated thread.
    """

    def __init__(
        self,
        lots_client: Any,
        filters: list[dict],
        auction_house: str | None,
        sample_size: int,
        seed: int,
        work_queue: queue.Queue,
        worker_count: int,
        shutdown_event: threading.Event,
    ) -> None:
        self._lots_client = lots_client
        self._filters = filters
        self._auction_house = auction_house
        self._sample_size = sample_size
        self._seed = seed
        self._work_queue = work_queue
        self._worker_count = worker_count
        self._shutdown_event = shutdown_event

    def run(self) -> int:
        """Produce sampled lot_items onto the queue. Returns total items produced."""
        _, total_lots = self._lots_client.query_lots_with_items_and_auction(
            filters=self._filters,
            auction_house=self._auction_house,
            return_count=True,
            limit=1,
            offset=0,
        )
        if not total_lots:
            print("[SampleProducer] No lots found for the given filters.")
            for _ in range(self._worker_count):
                self._work_queue.put(_SENTINEL)
            return 0

        sample_size = min(self._sample_size, total_lots)
        if sample_size < self._sample_size:
            print(
                f"[SampleProducer] sample-size ({self._sample_size}) > total "
                f"({total_lots}); using {sample_size}"
            )
        rng = random.Random(self._seed)
        offsets = sorted(rng.sample(range(total_lots), sample_size))
        print(
            f"[SampleProducer] Sampling {sample_size}/{total_lots} lots "
            f"(seed={self._seed})"
        )

        def _fetch(offset: int) -> dict | None:
            if self._shutdown_event.is_set():
                return None
            lots, _ = self._lots_client.query_lots_with_items_and_auction(
                filters=self._filters,
                auction_house=self._auction_house,
                order_by=["external_id"],
                limit=1,
                offset=offset,
            )
            return lots[0] if lots else None

        total_produced = 0
        try:
            with ThreadPoolExecutor(
                max_workers=16, thread_name_prefix="sample-fetch"
            ) as executor:
                for lot in executor.map(_fetch, offsets):
                    if lot is None or self._shutdown_event.is_set():
                        continue
                    for item in lot.get("lot_items", []):
                        self._work_queue.put({
                            "lot_item_id": item["id"],
                            "lot_offset": 0,
                            "wine_name": lot.get("lot_name") or "",
                            "lot_producer": item.get("lot_producer") or "",
                            "vintage": item.get("vintage"),
                            "region": lot.get("region"),
                            "sub_region": lot.get("sub_region"),
                            "country": lot.get("country"),
                            "colour": item.get("colour"),
                            "lot_external_id": lot.get("external_id"),
                        })
                        total_produced += 1
        except Exception as e:
            print(f"[SampleProducer] Fatal error: {e}")
            self._shutdown_event.set()
        finally:
            for _ in range(self._worker_count):
                self._work_queue.put(_SENTINEL)
            print(f"[SampleProducer] Done. Total items produced: {total_produced}")

        return total_produced
