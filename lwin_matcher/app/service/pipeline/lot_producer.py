from __future__ import annotations

import queue
import threading
from typing import Any
import logging

_SENTINEL = None  # Signals workers to stop


class LotProducer:
    """
    Reads lots from DB in pages and places each lot_item as a work unit onto the
    work_queue. When exhausted, places one sentinel (None) per worker thread.

    Runs in a single dedicated thread.
    """

    def __init__(
        self,
        lots_client: Any,
        filters: list[dict],
        auction_house: str | None,
        fetch_batch_size: int,
        start_offset: int,
        work_queue: queue.Queue,
        worker_count: int,
        shutdown_event: threading.Event,
    ) -> None:
        self._lots_client = lots_client
        self._filters = filters
        self._auction_house = auction_house
        self._batch_size = fetch_batch_size
        self._start_offset = start_offset
        self._work_queue = work_queue
        self._worker_count = worker_count
        self._shutdown_event = shutdown_event
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> int:
        """Produce all lot_items onto the queue. Returns total items produced."""
        total_produced = 0
        offset = self._start_offset

        # Get total count upfront for progress logging
        _, total_lots = self._lots_client.query_lots_with_items_and_auction(
            filters=self._filters,
            auction_house=self._auction_house,
            return_count=True,
            limit=1,
            offset=0,
        )
        total_batches = ((total_lots or 0) + self._batch_size - 1) // self._batch_size
        self.logger.info(
            f"[Producer] Total lots: {total_lots} "
            f"({total_batches} batches × {self._batch_size})"
        )

        try:
            while not self._shutdown_event.is_set():
                lots, _ = self._lots_client.query_lots_with_items_and_auction(
                    filters=self._filters,
                    auction_house=self._auction_house,
                    limit=self._batch_size,
                    offset=offset,
                )
                if not lots:
                    break

                items_in_batch = 0
                for lot in lots:
                    for item in lot.get("lot_items", []):
                        if self._shutdown_event.is_set():
                            return total_produced
                        self._work_queue.put({
                            "lot_item_id": item["id"],
                            "lot_offset": offset,
                            # Matching inputs
                            "wine_name": lot.get("lot_name") or "",
                            "lot_producer": item.get("lot_producer") or "",
                            "vintage": item.get("vintage"),
                            "region": lot.get("region"),
                            "sub_region": lot.get("sub_region"),
                            "country": lot.get("country"),
                            "colour": item.get("colour"),
                            # Extra context (used by sample CSV export)
                            "lot_external_id": lot.get("external_id"),
                        })
                        total_produced += 1
                        items_in_batch += 1

                batch_num = (offset - self._start_offset) // self._batch_size + 1
                self.logger.info(
                    f"[Producer] Batch {batch_num}/{total_batches} "
                    f"(offset={offset}): {len(lots)} lots → {items_in_batch} items queued"
                )
                offset += self._batch_size

        except Exception as e:
            print(f"[Producer] Fatal error at offset {offset}: {e}")
            self._shutdown_event.set()

        finally:
            # Always send one sentinel per worker so they can exit cleanly
            for _ in range(self._worker_count):
                self._work_queue.put(_SENTINEL)
            print(f"[Producer] Done. Total items produced: {total_produced}")

        return total_produced
