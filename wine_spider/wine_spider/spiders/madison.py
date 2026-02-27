import os
import json
import scrapy
import dotenv
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import (
    get_current_timestamp
)
from wine_spider.services.madison_client import MadisonClient

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class MadisonSpider(scrapy.Spider):
    name = "madison_spider"
    allowed_domains = [
        "api.madison-auction.com",
        "www.madison-auction.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "madison_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/madison",

        "PLAYWRIGHT_CONTEXTS": {
            "madison": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "locale": "en-US",
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0",
                },
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False,
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super(MadisonSpider, self).__init__(*args, **kwargs)
        self.madison_client = MadisonClient()

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.madison-auction.com/auctions",
            callback=self.parse,
            meta={
                "playwright": True,
                "playwright_context": "madison",
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "locale": "en-US",
                },
            },
        )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        html = await page.content()
        await page.close()

        selector = scrapy.Selector(text=html)
        all_auctions_container = selector.xpath("//div[contains(text(), 'All Auctions')]/following-sibling::*[1]").get()
        all_auction_cards = all_auctions_container.css("a").getall()

        for auction_card in all_auction_cards:
            details = auction_card.css("div.detail").get()

            auction = AuctionItem()
            auction["auction_title"] = auction_card.css("div.title::text").get()
            auction["auction_house"] = "Madison"
            auction["details"] = details
            yield auction
