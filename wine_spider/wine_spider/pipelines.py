# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from .database import DatabaseClient
from .items import AuctionItem, AuctionSalesItem, LotItem

class WineSpiderPipeline:
    def process_item(self, item, spider):
        return item


class DataStoragePipeline:
    def open_spider(self, spider):
        self.db_client = DatabaseClient(
            dbname="wine_admin",
            user="postgres",
            password="341319",
            host="localhost",
            port="5432"
        )

        self.lot_items_by_auction = {}

    def process_item(self, item, spider):
        item_data = ItemAdapter(item).asdict()

        if type(item) == AuctionItem:
            self.db_client.insert_item("auctions", item_data)
        elif type(item) == LotItem:
            auction_id = item_data.get('auction_id')
            if auction_id and item_data['success']:
                self.db_client.insert_item("lots", item_data)
            else:
                self.db_client.insert_item("failed_lots", item_data)
            self.lot_items_by_auction.setdefault(auction_id, []).append(item_data)
        else:
            raise ValueError(f"Unknown item type: {item.get('item_type')}")
        
        return item
    
    def close_spider(self, spider):
        auction_sales_item = AuctionSalesItem()
        
        for auction_id, lot_items in self.lot_items_by_auction.items():
            try:
                sold = 0
                total_low_estimate = 0
                total_high_estimate = 0
                total_sales = 0
                volumn_sold = 0
                top_lot = None
                top_lot_price = None
                current_cellar = None
                single_cellar = True

                for lot in lot_items:
                    sold += 1 if lot['sold'] else 0
                    total_low_estimate += lot['low_estimate']
                    total_high_estimate += lot['high_estimate']
                    total_sales += int(lot['end_price']) if lot['sold'] else 0
                    volumn_sold += lot['volumn'] if lot['sold'] and 'volumn' in lot else 0
                    if lot['sold'] and (not top_lot or int(lot['end_price']) > top_lot_price):
                        top_lot = lot['id']
                        top_lot_price = int(lot['end_price'])
                    if not current_cellar:
                        current_cellar = lot['lot_producer']
                    elif current_cellar != lot['lot_producer']:
                        single_cellar = False

                auction_sales_item['id'] = auction_id
                auction_sales_item['lots'] = len(lot_items)
                auction_sales_item['sold'] = sold
                auction_sales_item['currency'] = lot_items[0]['original_currency']
                auction_sales_item['total_low_estimate'] = total_low_estimate
                auction_sales_item['total_high_estimate'] = total_high_estimate
                auction_sales_item['total_sales'] = total_sales
                auction_sales_item['volumn_sold'] = volumn_sold
                auction_sales_item['value_sold'] = total_sales
                auction_sales_item['top_lot'] = top_lot
                auction_sales_item['sale_type'] = "PAST"
                auction_sales_item['single_cellar'] = single_cellar
                auction_sales_item['ex_ch'] = False

                item_data = ItemAdapter(auction_sales_item).asdict()
                self.db_client.insert_item("auction_sales", item_data)
            except Exception as e:
                print(f"Error processing auction {auction_id}: {e}")
                continue

        self.db_client.close()