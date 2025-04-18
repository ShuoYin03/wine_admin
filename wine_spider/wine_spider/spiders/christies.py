import os
import re
import json
import scrapy
import dotenv
import demjson3
from datetime import datetime
from wine_spider.items import AuctionItem
from wine_spider.helpers.christies.continent_parser import find_continent

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
            url = f"https://www.christies.com/en/results?year={year}&filters=|category_14|"
            yield scrapy.Request(
                url=url,
                callback=self.parse
            )

    def parse(self, response):
        script_text = response.text
        match = re.search(r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n', script_text, re.DOTALL)
        if not match:
            self.logger.error("calendar JSON not found")
            return

        calendar_json = demjson3.decode(match.group(1))
        events = calendar_json.get('data', {}).get('events', [])

        for event in events:
            auctionItem = AuctionItem()
            
            filters = event.get("filter_ids", "")
            if "category_14" in filters:
                auctionItem["id"] = event.get("event_id", None)
                auctionItem["auction_title"] = event.get("title_txt", None)
                auctionItem["auction_house"] = "Christie's"
                auctionItem["city"] = event.get("location_txt", None)
                auctionItem["continent"] = find_continent(auctionItem["city"])
                auctionItem["start_date"] = event.get("start_date", None)
                auctionItem["end_date"] = event.get("end_date", None)
                date = datetime.fromisoformat(auctionItem["start_date"]) if auctionItem["start_date"] else None
                auctionItem["year"] = date.year if date else None
                auctionItem["quarter"] = date.month // 4 + 1 if date else None
                auctionItem["auction_type"] = "LIVE" if event.get("is_live", None) else "PAST"
                auctionItem["url"] = event.get("landing_url", None)

                # yield auctionItem

                # auction_url = event.get("landing_url", None)
                # if auction_url:
                #     yield scrapy.Request(
                #         url=auction_url,
                #         callback=self.parse_auctions
                #     )

    def parse_auctions(self, response):
        pass