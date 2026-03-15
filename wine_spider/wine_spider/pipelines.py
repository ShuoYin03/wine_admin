from collections import defaultdict

from itemadapter import ItemAdapter
from psycopg2.errors import ForeignKeyViolation
from sqlalchemy.exc import IntegrityError

from shared.database.fx_rates_client import FxRatesClient

from .items import (
    AuctionItem,
    AuctionSalesItem,
    FxRateItem,
    FxRateItemList,
    LotDetailItem,
    LotItem,
    LwinMatchingItem,
)
from .services.database import (
    auction_sales_client,
    auctions_client,
    lot_items_client,
    lots_client,
    lwin_matching_client,
)


class BaseStoragePipeline:
    def open_spider(self, spider):
        self._retry_queue = []

    def safe_upsert(self, fn, data, spider, context):
        try:
            fn(data)
            return True
        except IntegrityError as exc:
            orig = getattr(exc, "orig", None)
            if isinstance(orig, ForeignKeyViolation):
                self._retry_queue.append((fn, data, context))
                spider.logger.warning(
                    "%s queued retry for %s due to FK violation",
                    self.__class__.__name__,
                    context,
                )
                return False
            raise

    def close_spider(self, spider):
        if not getattr(self, "_retry_queue", None):
            return

        retry_queue = self._retry_queue
        self._retry_queue = []
        spider.logger.info(
            "%s retrying %s deferred writes",
            self.__class__.__name__,
            len(retry_queue),
        )
        for fn, data, context in retry_queue:
            try:
                fn(data)
            except Exception as exc:  # noqa: BLE001
                spider.logger.error(
                    "%s final retry failed for %s: %s",
                    self.__class__.__name__,
                    context,
                    exc,
                )


class LwinMatchingPipeline(BaseStoragePipeline):
    def process_item(self, item, spider):
        if not isinstance(item, LwinMatchingItem):
            return item

        data = ItemAdapter(item).asdict()
        lot_id = data.get("lot_id")
        self.safe_upsert(
            lwin_matching_client.upsert_by_external_id,
            data,
            spider,
            f"lwin_matching lot_id={lot_id}",
        )
        return item


class AuctionStoragePipeline(BaseStoragePipeline):
    def process_item(self, item, spider):
        if not isinstance(item, AuctionItem):
            return item

        self.safe_upsert(
            auctions_client.upsert_by_external_id,
            ItemAdapter(item).asdict(),
            spider,
            f"auction external_id={item.get('external_id')}",
        )
        return item


class LotPipeline(BaseStoragePipeline):
    def open_spider(self, spider):
        super().open_spider(spider)
        self._processed_lots = set()
        self._pending_details = defaultdict(list)

    def _upsert_lot_detail(self, data):
        lot_items_client.upsert_by_external_id(data)

    def _flush_pending_details(self, lot_id, spider):
        pending_details = self._pending_details.pop(lot_id, [])
        for pending_detail in pending_details:
            self.safe_upsert(
                self._upsert_lot_detail,
                pending_detail,
                spider,
                f"lot_detail lot_id={lot_id}",
            )

    def process_item(self, item, spider):
        if isinstance(item, LotItem):
            data = ItemAdapter(item).asdict()
            lot_id = data["external_id"]
            inserted = self.safe_upsert(
                lots_client.upsert_by_external_id,
                data,
                spider,
                f"lot external_id={lot_id} auction_id={data.get('auction_id')}",
            )
            if inserted:
                lot_items_client.delete_by_external_id(lot_id)
                self._flush_pending_details(lot_id, spider)
                self._processed_lots.add(lot_id)
            return item

        if isinstance(item, LotDetailItem):
            data = ItemAdapter(item).asdict()
            lot_id = data["lot_id"]
            if lot_id in self._processed_lots:
                self.safe_upsert(
                    self._upsert_lot_detail,
                    data,
                    spider,
                    f"lot_detail lot_id={lot_id}",
                )
            else:
                self._pending_details[lot_id].append(data)
                spider.logger.debug(
                    "Buffered lot detail for lot_id=%s until parent lot arrives",
                    lot_id,
                )
        return item

    def close_spider(self, spider):
        super().close_spider(spider)
        for lot_id, pending_details in self._pending_details.items():
            spider.logger.error(
                "Dropping %s pending lot details because parent lot never arrived for lot_id=%s",
                len(pending_details),
                lot_id,
            )


class AuctionSalesAggregatorPipeline:
    def open_spider(self, spider):
        self.auction_sales = defaultdict(
            lambda: {
                "lots": 0,
                "sold": 0,
                "total_low_estimate": 0,
                "total_high_estimate": 0,
                "total_sales": 0,
                "volume_sold": 0,
                "top_lot": None,
                "top_lot_price": 0,
                "single_cellar_check": None,
                "single_cellar": True,
                "currency": None,
            }
        )
        self.lots_id_to_auction_id = {}

    def process_item(self, item, spider):
        data = ItemAdapter(item).asdict()

        if isinstance(item, LotItem):
            auction_id = data["auction_id"]
            lot_id = data["external_id"]
            self.lots_id_to_auction_id[lot_id] = auction_id
            stats = self.auction_sales[auction_id]

            stats["lots"] += 1
            if data.get("original_currency") and stats["currency"] is None:
                stats["currency"] = data["original_currency"]
            stats["total_low_estimate"] += int(data.get("low_estimate") or 0)
            stats["total_high_estimate"] += int(data.get("high_estimate") or 0)

            if data.get("sold"):
                price = int(data.get("end_price") or 0)
                stats["sold"] += 1
                stats["total_sales"] += price
                stats["volume_sold"] += float(data.get("volume") or 0)
                if price > stats["top_lot_price"]:
                    stats["top_lot_price"] = price
                    stats["top_lot"] = lot_id

            return item

        if isinstance(item, LotDetailItem):
            lot_id = data["lot_id"]
            auction_id = self.lots_id_to_auction_id.get(lot_id)
            if not auction_id:
                return item

            producer = data.get("lot_producer")
            if producer is None:
                return item

            stats = self.auction_sales[auction_id]
            if stats["single_cellar_check"] is None:
                stats["single_cellar_check"] = producer
            elif stats["single_cellar_check"] != producer:
                stats["single_cellar"] = False

        return item

    def close_spider(self, spider):
        for auction_id, stats in self.auction_sales.items():
            as_item = AuctionSalesItem()
            as_item["auction_id"] = auction_id
            as_item["lots"] = stats["lots"]
            as_item["sold"] = stats["sold"]
            as_item["currency"] = stats["currency"]
            as_item["total_low_estimate"] = stats["total_low_estimate"]
            as_item["total_high_estimate"] = stats["total_high_estimate"]
            as_item["total_sales"] = stats["total_sales"]
            as_item["volume_sold"] = stats["volume_sold"]
            as_item["top_lot"] = stats["top_lot"]
            as_item["sale_type"] = "PAST"
            as_item["single_cellar"] = stats["single_cellar"]
            as_item["ex_ch"] = False

            auction_sales_client.upsert_by_external_id(ItemAdapter(as_item).asdict())


class FxRatesStoragePipeline:
    def open_spider(self, spider):
        self.db_client = FxRatesClient()

    def process_item(self, item, spider):
        if isinstance(item, FxRateItemList):
            item_data = ItemAdapter(item).asdict()
            rows = item_data.get("rows") or []
            self.db_client.bulk_upsert(
                rows,
                index_elements=["rates_from", "rates_to", "date"],
            )
            return item

        if not isinstance(item, FxRateItem):
            return item

        item_data = ItemAdapter(item).asdict()
        self.db_client.upsert(
            item_data,
            index_elements=["rates_from", "rates_to", "date"],
        )
        return item
