import os
import dotenv
import scrapy
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.services.database import lots_client as default_lots_client


def has_stored_lots(auction_id, lot_client) -> bool:
    if hasattr(lot_client, "has_lots_for_auction"):
        return bool(lot_client.has_lots_for_auction(auction_id))
    return bool(lot_client.get_all_by_auction(auction_id))


def should_skip_existing_auction_record(
    auction_id,
    auction_client,
    lot_client=None,
    full_fetch: bool = False,
    logger=None,
) -> bool:
    if full_fetch or not auction_id:
        return False

    if auction_client.get_by_external_id(auction_id) is None:
        return False

    lot_client = lot_client or default_lots_client
    if has_stored_lots(auction_id, lot_client):
        if logger:
            logger.info("Auction %s already exists with lots in database. Skipping.", auction_id)
        return True

    if logger:
        logger.info("Auction %s exists but has no stored lots. Refetching lots.", auction_id)
    return False


class BaseAuctionSpider(scrapy.Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dotenv.load_dotenv()
        self.full_fetch = os.getenv("FULL_FETCH", "False").lower() == "true"

    def should_skip_existing_auction(self, auction_id, auction_client, lot_client=None) -> bool:
        return should_skip_existing_auction_record(
            auction_id,
            auction_client,
            lot_client=lot_client,
            full_fetch=self.full_fetch,
            logger=self.logger,
        )

    def check_auction_exists(self, auction_id, auction_client) -> bool:
        return self.should_skip_existing_auction(auction_id, auction_client)

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
