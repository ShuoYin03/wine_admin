from datetime import datetime
import os
import re
import scrapy
from urllib.parse import unquote, urlparse
from shared.database.auctions_client import AuctionsClient
from wine_spider.items import AuctionItem, LotItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.helpers import (
    remove_commas,
    wineauctioneer_parse_date,
    parse_unit_format,
    extract_unit_and_unit_format,
    expand_to_lot_items,
    build_lot_external_id,
)
from wine_spider.helpers.wineauctioneer.login import get_chrome_executable_path

BASE_URL = "https://wineauctioneer.com"
PAST_AUCTIONS_URL = f"{BASE_URL}/wine-auctions"


def navigation_headers(referer: str | None = None) -> dict[str, str]:
    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7,en-GB;q=0.6,en-US;q=0.5",
        "sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        ),
    }
    if referer:
        headers["referer"] = referer.split("#", 1)[0]
    return headers


def env_truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def playwright_launch_options() -> dict:
    options = {
        "headless": env_truthy("WINEAUCTIONEER_BROWSER_HEADLESS", True),
    }
    chrome_path = get_chrome_executable_path()
    if chrome_path:
        options["executable_path"] = chrome_path
    return options


def normalize_auction_id_for_url_filter(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or None


def auction_id_from_listing_link(link: str) -> str | None:
    path = unquote(urlparse(link).path)
    match = re.search(r"/wine-auctions/([^/]+)/lots/?$", path, flags=re.IGNORECASE)
    if not match:
        return None
    return normalize_auction_id_for_url_filter(match.group(1))


class WineAuctioneerSpider(BaseAuctionSpider):
    name = "wineauctioneer_spider"
    allowed_domains = [
        "wineauctioneer.com",
        "www.wineauctioneer.com"
    ]

    custom_settings = BaseAuctionSpider.build_custom_settings(
        "wineauctioneer.log",
        extra={
            "WINEAUCTIONEER_STATE_PATH": "wine_spider/login_state/wineauctioneer_cookies.json",
            "WINEAUCTIONEER_STATE_EXPIRE_DAYS": 107,
            "WINEAUCTIONEER_LOGIN_SCRIPT": "wine_spider/helpers/wineauctioneer/login.py",
            "PLAYWRIGHT_CONTEXTS": {
                "wineauctioneer": {
                    "storage_state": "wine_spider/login_state/wineauctioneer_cookies.json"
                }
            },
            "PLAYWRIGHT_LAUNCH_OPTIONS": playwright_launch_options(),
            "DOWNLOADER_MIDDLEWARES": {
                "wine_spider.middlewares.request_timing_middleware.RequestTimingMiddleware": 100,
                "wine_spider.middlewares.playwright_resource_blocker_middleware.PlaywrightResourceBlockerMiddleware": 200,
                "wine_spider.middlewares.wineauctioneer_login_middleware.WineauctioneerLoginMiddleware": 100,
            },
        },
    )

    start_urls = [
        PAST_AUCTIONS_URL
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                headers=navigation_headers(BASE_URL),
                meta=self.browser_meta(referer=BASE_URL),
            )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auction_client = AuctionsClient()
        self.use_browser = env_truthy("WINEAUCTIONEER_USE_BROWSER", True)
        self.backfill_auction_ids = {
            auction_id.strip()
            for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
            if auction_id.strip()
        }
        self.normalized_backfill_auction_ids = {
            normalized_id
            for normalized_id in (
                normalize_auction_id_for_url_filter(auction_id)
                for auction_id in self.backfill_auction_ids
            )
            if normalized_id
        }

    def browser_meta(self, referer: str | None = None):
        if not self.use_browser:
            return {}
        meta = {
            "playwright": True,
            "playwright_context": "wineauctioneer",
        }
        if referer:
            meta["playwright_page_goto_kwargs"] = {
                "referer": referer.split("#", 1)[0],
                "wait_until": "domcontentloaded",
            }
        return meta

    def parse(self, response):
        auction_links = response.css("a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)").getall()
        auction_links = set(auction_links)
        listing_url = response.url.split("#", 1)[0]
        
        for link in auction_links:
            if self.normalized_backfill_auction_ids:
                link_auction_id = auction_id_from_listing_link(link)
                if link_auction_id not in self.normalized_backfill_auction_ids:
                    self.logger.debug(
                        "Auction link %s is not in BACKFILL_AUCTION_IDS. Skipping request...",
                        link,
                    )
                    continue
            yield response.follow(
                link,
                self.parse_auction,
                headers=navigation_headers(listing_url),
                meta=self.browser_meta(referer=listing_url),
            )

        pagination_links = response.css("a[href*='page=']::attr(href)").getall()
        current_url = response.url.split("#", 1)[0]
        for link in set(pagination_links):
            if "0%2C0%2C0%2C0%2C0" in link or "0,0,0,0,0" in link:
                continue
            next_url = response.urljoin(link).split("#", 1)[0]
            if next_url == current_url:
                continue
            yield response.follow(
                link,
                self.parse,
                headers=navigation_headers(listing_url),
                meta=self.browser_meta(referer=listing_url),
            )
    
    def parse_auction(self, response):
        auction_item = AuctionItem()
        auction_item["external_id"] = response.css("h1.page-title::text").get().strip().replace(" ", "-").lower()
        if self.backfill_auction_ids and auction_item["external_id"] not in self.backfill_auction_ids:
            self.logger.debug(
                "Auction %s is not in BACKFILL_AUCTION_IDS. Skipping...",
                auction_item["external_id"],
            )
            return
        if self.check_auction_exists(auction_item["external_id"], self.auction_client):
            return

        auction_item["auction_title"] = response.css("h1.page-title::text").get().strip()
        auction_item["auction_house"] = "Wineauctioneer"
        auction_item["city"] = None
        auction_item["continent"] = None
        start_date = response.css("div.auction-info.field-hstack div:first-child div::text").get().strip()
        end_date = response.css("div.auction-info.field-hstack div:nth-child(2) div:last-child::text").get().strip()
        auction_item["start_date"] = datetime.strptime(start_date, "%d %B %Y").strftime("%Y-%m-%d")
        auction_item["end_date"] = datetime.strptime(end_date, "%d %B %Y").strftime("%Y-%m-%d")
        auction_item["year"] = auction_item["start_date"][:4]
        auction_item["quarter"] = (int(auction_item['start_date'][5:7]) - 1) // 3 + 1
        auction_item["auction_type"] = response.css("div.auction-status.auction-status-closed::text").get().strip()
        auction_item["url"] = response.url
        yield auction_item

        lot_links = response.css("h3.teaser-title a::attr(href)").getall()
        auction_url = response.url.split("#", 1)[0]
        for link in lot_links:
            yield response.follow(
                link,
                self.parse_lot,
                meta={
                    "auction_id": auction_item["external_id"],
                    **self.browser_meta(referer=auction_url),
                },
                headers=navigation_headers(auction_url),
                dont_filter=True,
            )

        next_page = response.xpath('//a[@rel="next"]/@href').get()
        if next_page:
            yield response.follow(
                next_page,
                self.parse_auction_next_page,
                meta={
                    "auction_id": auction_item["external_id"],
                    **self.browser_meta(referer=auction_url),
                },
                headers=navigation_headers(auction_url),
                dont_filter=True,
            )

    def parse_auction_next_page(self, response):
        auction_id = response.meta.get("auction_id", None)
        
        lot_links = response.css("h3.teaser-title a::attr(href)").getall()
        auction_url = response.url.split("#", 1)[0]
        for link in lot_links:
            yield response.follow(
                link,
                self.parse_lot,
                meta={
                    "auction_id": auction_id,
                    **self.browser_meta(referer=auction_url),
                },
                headers=navigation_headers(auction_url),
                dont_filter=True,
            )

        next_page = response.xpath('//a[@rel="next"]/@href').get()
        if next_page:
            yield response.follow(
                next_page,
                self.parse_auction_next_page,
                meta={
                    "auction_id": auction_id,
                    **self.browser_meta(referer=auction_url),
                },
                headers=navigation_headers(auction_url),
                dont_filter=True,
            )

    def parse_lot(self, response):
        auction_id = response.meta.get("auction_id", None)

        lot_item = LotItem()
        lot_item["auction_id"] = auction_id
        source_lot_id = response.css("div.mb-1::text").getall()[-1].strip()
        lot_item["external_id"] = build_lot_external_id(auction_id, source_lot_id)
        lot_item["lot_name"] = response.css("h1.page-title::text").get().strip()
        lot_type = response.css("div.field.field--name-field-type div.field__item::text").get()
        if lot_type:
            lot_item["lot_type"] = [lot_type.strip()]
        unit_info = response.css("div.field.field--name-field-size div.field__item::text").get()
        unit_format = None
        if unit_info:
            lot_item['volume'] = parse_unit_format(unit_info)
            lot_item['unit'], unit_format = extract_unit_and_unit_format(unit_info)
        price_info_html = response.css("div.bid__stat--text::text").get()
        if price_info_html:
            price_info = price_info_html.strip()
            lot_item["original_currency"] = price_info[0:1]
            lot_item["end_price"] = float(remove_commas(price_info[1:]))
            lot_item["sold"] = True
        else:
            lot_item["original_currency"] = None
            lot_item["end_price"] = None
            lot_item["sold"] = False
        sold_date = response.css("div.auction-info.hstack.gap-4 div > div::text").getall()[-1]
        lot_item["sold_date"] = wineauctioneer_parse_date(sold_date.strip()) if sold_date else None
        lot_item["success"] = True
        lot_item["url"] = response.url
        yield lot_item

        lot_producer = []
        if response.css("div.field.field--name-field-producer div.field__item a::text").get():
            lot_producer.append(response.css("div.field.field--name-field-producer div.field__item a::text").get().strip())
        vintage = []
        if response.css("div.field.field--name-field-vintage div.field__item::text").get():
            vintage.append(response.css("div.field.field--name-field-vintage div.field__item::text").get().strip())
        unit_format = [unit_format] if unit_format else []
        wine_colour = []
        if response.css("div.field.field--name-field-type div.field__item::text").get():
            wine_colour.append(response.css("div.field.field--name-field-type div.field__item::text").get().strip())
        
        lot_detail_items = expand_to_lot_items(
            lot_producer=lot_producer,
            vintage=vintage,
            unit_format=unit_format,
            wine_colour=wine_colour
        )

        for lot_detail_item in lot_detail_items:
            lot_detail_item['lot_id'] = lot_item['external_id']
            yield lot_detail_item
