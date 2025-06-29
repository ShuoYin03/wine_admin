import os
import scrapy
import dotenv
from wine_spider.services.steinfels_client import SteinfelsClient

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class SteinfelsSpider(scrapy.Spider):
    name = "steinfels_spider"
    allowed_domains = [
        "auktionen.steinfelsweine.ch"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "steinfels_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/steinfels",
    }

    custom_headers = {
        "x-api-version": "1.15",
    }

    def __init__(self, *args, **kwargs):
        super(SteinfelsSpider, self).__init__(*args, **kwargs)
        self.steinfels_client = SteinfelsClient()

    def start_requests(self):
        yield scrapy.Request(
            url=self.steinfels_client.auction_api_url,
            headers=self.custom_headers,
            callback=self.parse
        )

    def parse(self, response):
        auctions, auction_catalog_ids = self.steinfels_client.parse_auction_api_response(response.json())
        for i in range(len(auctions)):
            auction = auctions[i]
            auction_catalog_id = auction_catalog_ids[i]
            yield auction

            yield scrapy.Request(
                url=self.steinfels_client.get_lot_api_url(auction['url'].split('=')[-1]),
                headers=self.custom_headers,
                callback=self.parse_lots,
                meta={
                    'auction_catalog_id': auction_catalog_id
                }
            )
    
    def parse_lots(self, response):
        auction_catalog_id = response.meta.get('auction_catalog_id')
        current_page = response.meta.get('page', 1)

        results = self.steinfels_client.parse_lot_api_response(
            response=response.json(), 
            auction_catalog_id=auction_catalog_id,
            url=response.url
        )

        for result in results:
            yield result[0]

            for lot_detail_item in result[1]:
                yield lot_detail_item
        
        yield scrapy.Request(
            url=self.steinfels_client.get_lot_api_url(auction_catalog_id, page=current_page + 1),
            headers=self.custom_headers,
            callback=self.parse_lots,
            meta={
                'auction_catalog_id': auction_catalog_id,
                'page': current_page
            }
        )