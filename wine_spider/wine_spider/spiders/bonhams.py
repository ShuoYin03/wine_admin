import json
import os
import scrapy
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
            "CONCURRENT_REQUESTS": 2,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
            "DOWNLOAD_DELAY": 1.0,
            "RANDOMIZE_DOWNLOAD_DELAY": True,
            "AUTOTHROTTLE_ENABLED": True,
            "AUTOTHROTTLE_START_DELAY": 2.0,
            "AUTOTHROTTLE_MAX_DELAY": 15.0,
            "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
            "RETRY_TIMES": 8,
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
        self.backfill_auction_ids = {
            auction_id.strip()
            for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
            if auction_id.strip()
        }

    def start_requests(self):
        current_page = 1
        per_page = 250
        payload = self.bonhams_client.get_auction_search_payload(
            page=current_page,
            per_page=per_page,
        )

        yield scrapy.Request(
            url=self.bonhams_client.api_url,
            headers=self.bonhams_client.headers,
            method="POST",
            body=json.dumps(payload),
            callback=self.parse,
            meta={
                "current_page": current_page,
                "per_page": per_page,
            },
        )

    def parse(self, response):
        data = response.json()
        current_page = response.meta.get("current_page", 1)
        per_page = response.meta.get("per_page", 250)

        auctions = self.bonhams_client.parse_auction_api_response(data)
        for auction in auctions:
            auction_id = auction["external_id"]
            if self.backfill_auction_ids and auction_id not in self.backfill_auction_ids:
                self.logger.debug(f"Auction {auction_id} is not in BACKFILL_AUCTION_IDS. Skipping...")
                continue

            if self.check_auction_exists(auction_id, self.auction_client):
                continue

            yield auction
            payload = self.bonhams_client.get_lot_search_payload(auction_id)

            yield scrapy.Request(
                url=self.bonhams_client.api_url,
                method="POST",
                headers=self.bonhams_client.headers,
                body=json.dumps(payload),
                callback=self.parse_lots,
                meta={
                    "auction_id": auction_id
                },
            )

        if self.has_full_auction_page(data, per_page):
            next_page = current_page + 1
            payload = self.bonhams_client.get_auction_search_payload(
                page=next_page,
                per_page=per_page,
            )
            yield scrapy.Request(
                url=self.bonhams_client.api_url,
                method="POST",
                headers=self.bonhams_client.headers,
                body=json.dumps(payload),
                callback=self.parse,
                meta={
                    "current_page": next_page,
                    "per_page": per_page,
                },
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

    def has_full_auction_page(self, data, per_page: int) -> bool:
        hits = (
            data.get("results", [{}])[0]
            .get("hits", [])
        )
        return len(hits) >= per_page
