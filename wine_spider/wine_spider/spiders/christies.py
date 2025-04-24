import os
import re
import scrapy
import dotenv
import demjson3
from datetime import datetime
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import find_continent, parse_year_from_title

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ChristiesSpider(scrapy.Spider):
    name = "christies_spider"
    allowed_domains = [
        "www.christies.com",
        "onlineonly.christies.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "christies_log.txt"
    }

    def __init__(self, *args, **kwargs):
        super(ChristiesSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        year_list = [i for i in range(2007, 2008)]

        for year in year_list:
            for month in range(4, 5):
                url = f"https://www.christies.com/en/results?year={year}&filters=|category_14|&month={month}"

                yield scrapy.Request(
                    url=url,
                    callback=self.parse
                )

    def parse(self, response):
        match = re.search(r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n', response.text, re.DOTALL)
        if not match:
            self.logger.error("calendar not found")
            return

        data = demjson3.decode(match.group(1))
        events = data.get('data', {}).get('events', [])

        for event in events:
            filters = event.get("filter_ids", "")

            if "category_14" in filters:
                auctionItem = AuctionItem()
                auctionItem["id"] = event.get("event_id", None)
                auctionItem["auction_title"] = event.get("title_txt", None)
                auctionItem["auction_house"] = "Christie's"
                auctionItem["city"] = event.get("location_txt", None)
                auctionItem["continent"] = find_continent(auctionItem["city"])
                start_date = event.get("start_date", None)
                end_date = event.get("end_date", None)
                auctionItem["start_date"] = datetime.fromisoformat(start_date).date()
                auctionItem["end_date"] = datetime.fromisoformat(end_date).date()
                auctionItem["year"] = auctionItem["start_date"].year if start_date else None
                auctionItem["quarter"] = auctionItem["start_date"].month // 4 + 1 if start_date else None
                auctionItem["auction_type"] = "LIVE" if event.get("is_live", None) else "PAST"
                auctionItem["url"] = event.get("landing_url", None)

                # yield auctionItem

                if auctionItem["url"]:
                    yield scrapy.Request(
                        url=auctionItem["url"],
                        callback=self.parse_auctions
                    )

    def parse_auctions(self, response):
        match = re.search(r'window\.chrComponents\.lots\s*=\s*({.*?});\s*\n', response.text, re.DOTALL)
        if not match:
            self.logger.error("lots not found")
            return

        data = demjson3.decode(match.group(1)).get('data', {})
        filters = data.get('filters', []).get("groups", [])
        origin_filter = [filter.get("filters") for filter in filters if filter.get("title_txt") == "Origin"]
        if not origin_filter:
            lots = data.get("lots", [])
            for lot in lots:
                self.parse_single_lot(lot)
        else:
            for filter in origin_filter:
                self.logger.info(filter)

    
    def parse_single_lot(self, lot):
        lot_item = LotItem()
        lot_item["id"] = lot.get("object_id", None)
        # lot_item["auction_id"] = 
        # lot_item["lot_producer"] = 
        lot_item["wine_name"] = lot.get("title_primary_txt", None)
        lot_item["vintage"] = parse_year_from_title(lot_item["wine_name"])
        # lot_item["unit_format"] = 
        # lot_item["unit"] = 
        # lot_item["volumn"] = 
        # lot_item["lot_type"] = 
        # lot_item["wine_type"] = 
        # lot_item["original_currency"] = 
        # lot_item["start_price"] = 
        lot_item["end_price"] = lot.get("price_realised", None)
        lot_item["low_estimate"] = lot.get("estimate_low", None)
        lot_item["high_estimate"] = lot.get("estimate_high", None)
        # lot_item["sold"] = 
        lot_item["sold_date"] = lot.get("end_date", None)
        # lot_item["region"] = 
        # lot_item["sub_region"] = 
        # lot_item["country"] = 
        # lot_item["success"] = 
        lot_item["url"] = lot.get("url", None)

        # yield lot_item

            
