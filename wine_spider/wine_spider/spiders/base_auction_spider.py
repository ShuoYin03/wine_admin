import os
import dotenv
import scrapy
from wine_spider.spiders.logging_utils import build_spider_log_file

class BaseAuctionSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dotenv.load_dotenv()
        self.full_fetch = os.getenv("FULL_FETCH", "False").lower() == "true"

    def check_auction_exists(self, auction_id, auction_client) -> bool:
        if not self.full_fetch and auction_client.query_single_auction(auction_id) is not None:
            self.logger.info(
                "Auction %s already exists in database. Skipping.", auction_id
            )
            return True
        return False

    @classmethod
    def build_custom_settings(cls, log_filename: str, extra: dict | None = None) -> dict:
        """
        Return a base settings dict. Merge additional auction-house-specific
        settings with the *extra* argument.
        """
        settings = {
            "ROBOTSTXT_OBEY": False,
            "LOG_FILE": build_spider_log_file(log_filename),
        }
        if extra:
            settings.update(extra)
        return settings
