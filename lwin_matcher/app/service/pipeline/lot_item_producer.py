from __future__ import annotations

import logging
import queue
import threading
from typing import Any

_SENTINEL = None


class LotItemProducer:
    """
    Reads eligible lot_items with a stable keyset cursor and places each item
    onto the work queue.
    """

    def __init__(
        self,
        lots_client: Any,
        filters: list[dict],
        auction_house: str | None,
        fetch_batch_size: int,
        start_after_id: int,
        only_missing: bool,
        work_queue: queue.Queue,
        worker_count: int,
        shutdown_event: threading.Event,
    ) -> None:
        self._lots_client = lots_client
        self._filters = filters
        self._auction_house = auction_house
        self._batch_size = fetch_batch_size
        self._start_after_id = start_after_id
        self._only_missing = only_missing
        self._work_queue = work_queue
        self._worker_count = worker_count
        self._shutdown_event = shutdown_event
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> int:
        total_produced = 0
        last_lot_item_id = self._start_after_id

        _, total_items = self._lots_client.query_lot_items_for_lwin_matching(
            filters=self._filters,
            auction_house=self._auction_house,
            last_lot_item_id=last_lot_item_id,
            only_missing=self._only_missing,
            return_count=True,
            limit=1,
        )
        total_batches = ((total_items or 0) + self._batch_size - 1) // self._batch_size
        mode = "missing" if self._only_missing else "full"
        self.logger.info(
            f"[Producer] Total {mode} lot_items: {total_items} "
            f"({total_batches} batches x {self._batch_size})"
        )

        try:
            while not self._shutdown_event.is_set():
                rows, _ = self._lots_client.query_lot_items_for_lwin_matching(
                    filters=self._filters,
                    auction_house=self._auction_house,
                    last_lot_item_id=last_lot_item_id,
                    only_missing=self._only_missing,
                    limit=self._batch_size,
                )
                if not rows:
                    break

                for row in rows:
                    if self._shutdown_event.is_set():
                        return total_produced
                    lot_item_id = int(row["lot_item_id"])
                    self._work_queue.put({
                        "lot_item_id": lot_item_id,
                        "checkpoint_id": lot_item_id,
                        "lot_offset": lot_item_id,
                        "wine_name": row.get("wine_name") or "",
                        "lot_producer": row.get("lot_producer") or "",
                        "vintage": row.get("vintage"),
                        "region": row.get("region"),
                        "sub_region": row.get("sub_region"),
                        "country": row.get("country"),
                        "colour": row.get("colour"),
                        "lot_external_id": row.get("lot_external_id"),
                    })
                    total_produced += 1
                    last_lot_item_id = max(last_lot_item_id, lot_item_id)

                batch_num = (total_produced + self._batch_size - 1) // self._batch_size
                self.logger.info(
                    f"[Producer] Batch {batch_num}/{total_batches} "
                    f"(last_lot_item_id={last_lot_item_id}): {len(rows)} items queued"
                )

        except Exception as e:
            print(f"[Producer] Fatal error after lot_item_id {last_lot_item_id}: {e}")
            self._shutdown_event.set()

        finally:
            for _ in range(self._worker_count):
                self._work_queue.put(_SENTINEL)
            print(f"[Producer] Done. Total items produced: {total_produced}")

        return total_produced
