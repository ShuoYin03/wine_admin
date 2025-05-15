from itemadapter import ItemAdapter
from .services.database import (
    lots_client,
    auctions_client,
    lot_items_client,
    auction_sales_client,
    lwin_matching_client
)
from .items import (
    AuctionItem, 
    AuctionSalesItem,
    LotItem, 
    LotDetailItem,
    LwinMatchingItem, 
    FxRateItem,
)
from collections import defaultdict
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import ForeignKeyViolation

class LwinMatchingPipeline:
    def __init__(self):
        self.to_retry = []

    def process_item(self, item, spider):
        if isinstance(item, LwinMatchingItem):
            data = ItemAdapter(item).asdict()
            try:
                lwin_matching_client.upsert_by_external_id(data)
            except IntegrityError as e:
                orig = getattr(e, "orig", None)
                if isinstance(orig, ForeignKeyViolation):
                    spider.logger.warning(f"FK violation inserting LWIN for lot {item['external_id']}, retrying later...")
                    self.to_retry.append(data)
                    return item
                raise

        return item
        
    def close_spider(self, spider):
        if not self.to_retry:
            return

        spider.logger.info(f"Retrying {len(self.to_retry)} failed LWIN inserts…")
        for record in self.to_retry:
            lot_id = record.get('lot_id')
            try:
                lwin_matching_client.upsert_by_external_id(record)
                spider.logger.info(f"Retried LWIN insert for lot {lot_id} → OK")
            except IntegrityError as e:
                spider.logger.error(f"Final retry failed for LWIN of lot {lot_id}: {e}")

class AuctionStoragePipeline:
    def process_item(self, item, spider):
        if isinstance(item, AuctionItem):
            auctions_client.upsert_by_external_id(ItemAdapter(item).asdict())
        return item
    
class LotStoragePipeline:
    def __init__(self):
        self.to_retry = []
    
    def process_item(self, item, spider):
        if isinstance(item, LotItem):
            data = ItemAdapter(item).asdict()
            try:
                lots_client.upsert_by_external_id(data)
                lot_items_client.delete_by_external_id(item['external_id'])
            except IntegrityError as e:
                orig = getattr(e, "orig", None)
                if isinstance(orig, ForeignKeyViolation):
                    spider.logger.warning(f"FK violation inserting lot {item['external_id']}, retrying later...")
                    self.to_retry.append((data, item['external_id'], item['auction_id']))
                    return item
                raise

        return item
    
    def close_spider(self, spider):
        if not self.to_retry:
            return
        
        spider.logger.info(f"Retrying {len(self.to_retry)} failed Lot insertions...")
        for data, lot_id, auction_id in self.to_retry:
            try:
                lots_client.upsert_by_external_id(data)
                spider.logger.info(f"Successfully retried Lot {lot_id} for Auction {auction_id}")
            except IntegrityError as e:
                spider.logger.warning(f"Failed to retry Lot {lot_id} for Auction {auction_id}: {e}")
    

class LotDetailStoragePipeline:
    def process_item(self, item, spider):
        if isinstance(item, LotDetailItem):
            lot_items_client.upsert(ItemAdapter(item).asdict())
        return item


class AuctionSalesPipeline:
    def open_spider(self, spider):
        self.auction_sales = defaultdict(lambda: {
            "lots": 0,
            "sold": 0,
            "total_low_estimate": 0,
            "total_high_estimate": 0,
            "total_sales": 0,
            "volume_sold": 0,
            "value_sold": 0,
            "top_lot": None,
            "top_lot_price": 0,
            "single_cellar_check": None,
            "single_cellar": True,
            "currency": None
        })
        self.lots_id_to_auction_id = {}

    def process_item(self, item, spider):
        data = ItemAdapter(item).asdict()

        if isinstance(item, LotItem):
            auction_id = data['auction_id']
            lot_id = data['external_id']
            self.lots_id_to_auction_id[lot_id] = auction_id
            stats = self.auction_sales[auction_id]

            stats["lots"] += 1
            stats["currency"] = data['original_currency']
            if data.get('sold'):
                price = int(data.get('end_price') or 0)
                stats["sold"] += 1
                stats["total_sales"] += price
                stats["value_sold"] += price
                stats["volume_sold"] += float(data.get('volume') or 0)
                stats["total_low_estimate"]  += int(data.get('low_estimate') or 0)
                stats["total_high_estimate"] += int(data.get('high_estimate') or 0)
                if price > stats["top_lot_price"]:
                    stats["top_lot_price"] = price
                    stats["top_lot"] = lot_id

        elif isinstance(item, LotDetailItem):
            lot_id = data['lot_id']
            auction_id = self.lots_id_to_auction_id.get(lot_id)
            if auction_id:
                stats = self.auction_sales[auction_id]
                producer = data.get('lot_producer')
                if stats["single_cellar_check"] is None:
                    stats["single_cellar_check"] = producer
                elif stats["single_cellar_check"] != producer:
                    stats["single_cellar"] = False

        return item

    def close_spider(self, spider):
        for auction_id, stats in self.auction_sales.items():
            as_item = AuctionSalesItem()
            as_item['auction_id']           = auction_id
            as_item['lots']                 = stats['lots']
            as_item['sold']                 = stats['sold']
            as_item['currency']             = stats['currency']
            as_item['total_low_estimate']   = stats['total_low_estimate']
            as_item['total_high_estimate']  = stats['total_high_estimate']
            as_item['total_sales']          = stats['total_sales']
            as_item['volume_sold']          = stats['volume_sold']
            as_item['value_sold']           = stats['value_sold']
            as_item['top_lot']              = stats['top_lot']
            as_item['sale_type']            = "PAST"
            as_item['single_cellar']        = stats['single_cellar']
            as_item['ex_ch']                = False

            auction_sales_client.upsert_by_external_id(ItemAdapter(as_item).asdict())



# class FxRatesStoragePipeline:
#     def open_spider(self, spider):
#         self.db_client = DatabaseClient()

#     def process_item(self, item, spider):
#         if type(item) != FxRateItem:
#             return item
        
#         item_data = ItemAdapter(item).asdict()
#         self.db_client.insert_item("fx_rates_cache", item_data)

#         return item

#     def close_spider(self, spider):
#         self.db_client.close()