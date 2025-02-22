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

    def close_spider(self, spider):
        self.db_client.close()

    def process_item(self, item, spider):
        item_data = ItemAdapter(item).asdict()

        if type(item) == AuctionItem:
            self.db_client.insert_item("auctions", item_data)
        elif type(item) == AuctionSalesItem:
            self.db_client.insert_item("auction_sales", item_data)
        elif type(item) == LotItem:
            if item.get('success'):
                self.db_client.insert_item("lots", item_data)
            else:
                self.db_client.insert_item("failed_lots", item_data)
        else:
            raise ValueError(f"Unknown item type: {item.get('item_type')}")
        
        return item