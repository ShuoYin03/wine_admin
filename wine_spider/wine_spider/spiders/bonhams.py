import os
import json
import scrapy
import dotenv
from shared.database.auctions_client import AuctionsClient
from wine_spider.services.bonhams_client import BonhamsClient
from wine_spider.services.lot_information_finder import LotInformationFinder

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
        self.auction_client = AuctionsClient()
        self.lot_information_finder = LotInformationFinder()

    def start_requests(self):
        payload = self.bonhams_client.get_auction_search_payload()

        yield scrapy.Request(
            url=self.bonhams_client.api_url,
            headers=self.bonhams_client.headers,
            method="POST",
            body=json.dumps(payload),
            callback=self.parse
        )

    def parse(self, response):
        data = response.json()

        auctions = self.bonhams_client.parse_auction_api_response(data)
        for auction in auctions:
            if not FULL_FETCH and self.auction_client.query_single_auction(auction.external_id) is not None:
                self.logger.info(f"Auction {auction.external_id} already exists in database. Skipping.")
                return
        
            yield auction
            payload = self.bonhams_client.get_lot_search_payload(auction['external_id'])

            yield scrapy.Request(
                url=self.bonhams_client.api_url,
                method="POST",
                headers=self.bonhams_client.headers,
                body=json.dumps(payload),
                callback=self.parse_lots,
                meta={
                    "auction_id": auction['external_id']
                }
            )

    def parse_lots(self, response):
        data = response.json()
        auction_id = response.meta.get("auction_id")
        current_page = response.meta.get("current_page", 1)

        lots = self.bonhams_client.parse_lot_api_response(data)
        if lots:
            for lot in lots:
                yield lot[0]

                for lot_detail in lot[1]:
                    yield lot_detail

            payload = self.bonhams_client.get_lot_search_payload(auction_id, current_page + 1)

            yield scrapy.Request(
                url=self.bonhams_client.api_url,
                method="POST",
                headers=self.bonhams_client.headers,
                body=json.dumps(payload),
                callback=self.parse_lots,
                meta={
                    "auction_id": auction_id,
                    "current_page": current_page + 1
                }   
            )