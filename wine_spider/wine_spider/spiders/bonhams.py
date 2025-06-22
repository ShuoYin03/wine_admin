import os
import json
import scrapy
import dotenv
from wine_spider.services import BonhamsClient, LotInformationFinder

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class BonhamsSpider(scrapy.Spider):
    name = "bonhams_spider"
    allowed_domains = [
        "bonhams.com", 
        "api01.bonhams.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "bonhams_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/bonhams",
        "DOWNLOADER_MIDDLEWARES": {
            'wine_spider.middlewares.bonhams_header_middleware.BonhamsHeadersMiddleware': 543,
        },
    }

    def __init__(self, *args, **kwargs):
        super(BonhamsSpider, self).__init__(*args, **kwargs)
        self.bonhams_client = BonhamsClient()
        self.lot_information_finder = LotInformationFinder()

    def start_requests(self):
        payload = self.bonhams_client.get_auction_search_payload()
        
        yield scrapy.Request(
            url=self.bonhams_client.api_url,
            method="POST",
            body=json.dumps(payload),
            callback=self.parse
        )

    def parse(self, response):
        data = response.json()

        auctions = self.bonhams_client.parse_auction_api_response(data)
        for auction in auctions:
            yield auction
            payload = self.bonhams_client.get_lot_search_payload(auction['external_id'])

            yield scrapy.Request(
                url=self.bonhams_client.api_url,
                method="POST",
                body=json.dumps(payload),
                callback=self.parse_lots
            )

    def parse_lots(self, response):
        data = response.json()

        lots = self.bonhams_client.parse_lot_api_response(data)

        for lot in lots:
            yield lot[0]

            for lot_detail in lot[1]:
                yield lot_detail