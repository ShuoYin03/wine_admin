import json
from shared.database.auctions_client import AuctionsClient
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.services.bonhams_client import BonhamsClient
from wine_spider.services.lot_information_finder import LotInformationFinder


class BonhamsSpider(BaseAuctionSpider):
    name = "bonhams_spider"
    allowed_domains = [
        "bonhams.com",
        "api01.bonhams.com",
    ]

    custom_settings = BaseAuctionSpider.build_custom_settings(
        "bonhams.log",
        extra={
            # "JOBDIR": "wine_spider/crawl_state/bonhams",
            "DOWNLOADER_MIDDLEWARES": {
                "wine_spider.middlewares.bonhams_header_middleware.BonhamsHeadersMiddleware": 543,
            },
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            if self.check_auction_exists(auction.external_id, self.auction_client):
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
