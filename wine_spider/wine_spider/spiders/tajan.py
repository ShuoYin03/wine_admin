import os
import re
import unicodedata
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
import scrapy
import dotenv
import pandas as pd
from scrapy_playwright.page import PageMethod
from shared.database.auctions_client import AuctionsClient
from wine_spider.items import AuctionItem, LotItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.helpers.tajan.progress import TajanProgressTracker
from wine_spider.helpers import (
    generate_external_id,
    extract_month_year_and_format,
    find_continent,
    symbol_to_currency,
    remove_commas,
    extract_price_range,
    extract_years,
    match_lot_info,
    expand_to_lot_items,
    build_lot_external_id,
    TajanLotDetailParser,
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")


def parse_tajan_proxy_entry(entry: str) -> dict:
    entry = (entry or "").strip()
    if not entry:
        raise ValueError("Empty Tajan proxy entry")

    if "://" in entry:
        parsed = urlsplit(entry)
        if not parsed.hostname or not parsed.port:
            raise ValueError(f"Invalid Tajan proxy URL: {entry!r}")
        proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            proxy["username"] = unquote(parsed.username)
        if parsed.password:
            proxy["password"] = unquote(parsed.password)
        return proxy

    parts = entry.split(":", 3)
    if len(parts) not in (2, 4):
        raise ValueError(f"Invalid Tajan proxy entry: {entry!r}")

    host, port = parts[0].strip(), parts[1].strip()
    if not host or not port:
        raise ValueError(f"Invalid Tajan proxy host/port: {entry!r}")

    proxy = {"server": f"http://{host}:{port}"}
    if len(parts) == 4:
        proxy["username"] = parts[2]
        proxy["password"] = parts[3]
    return proxy


def build_tajan_proxy_contexts(raw_proxies: str | None = None) -> dict:
    raw_proxies = os.getenv("TAJAN_PROXY_URLS", "") if raw_proxies is None else raw_proxies
    entries = [
        entry.strip()
        for entry in re.split(r"[\s,]+", raw_proxies or "")
        if entry.strip()
    ]
    return {
        f"tajan_proxy_{index}": {"proxy": parse_tajan_proxy_entry(entry)}
        for index, entry in enumerate(entries)
    }


class TajanSpider(BaseAuctionSpider):
    name = "tajan_spider"
    allowed_domains = [
        "tajan.com",
        "www.tajan.com",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_LEVEL": "INFO",
        "LOG_FILE": build_spider_log_file("tajan.log"),
        "DOWNLOADER_MIDDLEWARES": {
            "wine_spider.middlewares.request_timing_middleware.RequestTimingMiddleware": 100,
            "wine_spider.middlewares.playwright_resource_blocker_middleware.PlaywrightResourceBlockerMiddleware": 200,
            "wine_spider.middlewares.tajan_curl_cffi_middleware.TajanCurlCffiMiddleware": 543,
        },
        "PLAYWRIGHT_ABORT_REQUEST": "wine_spider.middlewares.playwright_resource_blocker_middleware.should_abort_request",
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 2,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "DOWNLOAD_DELAY": 1.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504, 522, 524],
        "TAJAN_CURL_CFFI_ENABLED": True,
        "TAJAN_CURL_CFFI_MAX_ATTEMPTS": 3,
        "TAJAN_CURL_CFFI_TIMEOUT": 45,
        "TAJAN_CURL_CFFI_IMPERSONATES": ["chrome142", "chrome136", "chrome131", "chrome124"],
        "REQUEST_TIMING_SUCCESS_SAMPLE_RATE": 25,
        "REQUEST_TIMING_SLOW_SECONDS": 30,
        # "JOBDIR": "wine_spider/crawl_state/tajan",
    }

    def __init__(self, *args, **kwargs):
        super(TajanSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))
        self.auction_client = AuctionsClient()
        self.lot_detail_parser = TajanLotDetailParser()
        self.progress_tracker = TajanProgressTracker()
        self.discovered_auction_items = {}
        self.playwright_context_specs = self.build_playwright_context_specs()
        self._playwright_context_index = 0
        self.backfill_auction_ids = {
            auction_id.strip()
            for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
            if auction_id.strip()
        }

    def start_requests(self):
        direct_requests = list(self.start_backfill_requests_from_db())
        if direct_requests:
            yield from direct_requests
            return

        yield scrapy.Request(
            url="https://www.tajan.com/en/past/",
            callback=self.parse,
            meta=self.playwright_meta(),
        )

    def start_backfill_requests_from_db(self):
        target_ids = self.target_auction_ids()
        if not target_ids:
            return

        records = []
        for auction_id in sorted(target_ids):
            record = self.auction_client.get_by_external_id(auction_id)
            auction_url = getattr(record, "url", None) if record is not None else None
            if not auction_url:
                self.logger.info(
                    "Tajan direct backfill unavailable for auction_id=%s; falling back to discovery",
                    auction_id,
                )
                return
            records.append((auction_id, record, auction_url))

        progress = self.progress()
        for auction_id, record, auction_url in records:
            progress.record_discovered_auction(
                auction_id,
                getattr(record, "auction_title", None) or auction_id,
                auction_url,
            )
            progress.mark_queued(auction_id)
        progress.complete_discovery()
        self.logger.info(progress.discovery_log_line())

        for auction_id, record, auction_url in records:
            self.logger.info(
                "Tajan direct backfill: queued auction auction_id=%s title=%r url=%s",
                auction_id,
                getattr(record, "auction_title", None),
                auction_url,
            )
            self.logger.info(progress.auction_progress_log_line())
            yield scrapy.Request(
                url=auction_url,
                callback=self.enter_auction_page,
                errback=self.parse_catalog_error,
                meta=self.playwright_meta({
                    "auction_id": auction_id,
                }),
            )

    async def parse(self, response):
        progress = self.progress()
        container = response.css("div#plab__results-container")
        auctions = container.css("div.widget-event")
        page_wine_candidates = 0

        for auction in auctions:
            title_text = self.clean_text(auction.css("h2.event__title a::text").get())
            title = title_text.lower()
            if "wine" in title or "spirits" in title:
                page_wine_candidates += 1
                raw_date = auction.css("div.event__date::text").get()
                raw_time = auction.css("div.event__time.mb-0::text").get()

                auction_item = AuctionItem()
                auction_item["external_id"] = f"tajan_{generate_external_id(f"{title} {raw_date} {raw_time}")}"
                if self.target_auction_ids() and auction_item["external_id"] not in self.target_auction_ids():
                    self.logger.debug(f"Auction {auction_item['external_id']} is not in BACKFILL_AUCTION_IDS. Skipping...")
                    continue
                auction_item["auction_title"] = title_text
                auction_item["auction_house"] = "Tajan"
                auction_item["city"] = auction.css("div.event__location.mb-0::text").get().split(",")[0].strip()
                auction_item["continent"] = find_continent(auction.css("div.event__location.mb-0::text").get().split(",")[0].strip())
                
                raw_dates = self.extract_raw_dates_from_event_date(raw_date)
                if len(raw_dates) == 1:
                    month, year, start_date = extract_month_year_and_format(raw_dates[0])
                    auction_item["start_date"] = start_date
                    auction_item["end_date"] = start_date
                    auction_item["year"] = year
                    auction_item["quarter"] = (month - 1) // 3 + 1
                elif len(raw_dates) == 2:
                    print(raw_dates)
                    month, year, start_date = extract_month_year_and_format(raw_dates[0])
                    _, _, end_date = extract_month_year_and_format(raw_dates[1])
                    auction_item["start_date"] = start_date
                    auction_item["end_date"] = end_date
                    auction_item["year"] = year
                    auction_item["quarter"] = (month - 1) // 3 + 1
                auction_item["auction_type"] = "PAST"
                auction_url = auction.css("h2.event__title a::attr(href)").get()
                auction_item["url"] = auction_url
                progress.record_discovered_auction(
                    auction_item["external_id"],
                    auction_item["auction_title"],
                    auction_url,
                )
                self.discovered_auctions()[auction_item["external_id"]] = (
                    auction_item,
                    auction_url,
                )

        next_page = response.css("a.next.pagination::attr(href)").get()
        progress.record_discovery_page(
            page_url=response.url,
            page_auctions=len(auctions),
            wine_candidates=page_wine_candidates,
            has_next_page=bool(next_page),
        )
        self.logger.info(progress.discovery_log_line())
        if next_page:
            yield response.follow(
                next_page, 
                self.parse,
                meta=self.playwright_meta()
            )
            return

        progress.complete_discovery()
        self.logger.info(progress.discovery_log_line())
        for result in self.schedule_discovered_auctions(response):
            yield result
    
    def enter_auction_page(self, response):
        auction_id = response.meta.get("auction_id", None)
        if auction_id:
            self.progress().mark_started(auction_id)
            self.logger.info(self.progress().auction_progress_log_line())

        auction_link = self.select_auction_catalog_link(response)

        if auction_link:
            yield response.follow(
                url=self.build_catalog_url(auction_link),
                callback=self.parse_auction_page,
                errback=self.parse_catalog_error,
                meta=self.catalog_playwright_meta({
                    "auction_id": auction_id
                })
            )
        else:
            self.logger.warning(f"No auction link found for URL: {response.url}")
            yield from self.parse_auction_page(response)

    def select_auction_catalog_link(self, response):
        links = list(response.css("div.sale-ctas a"))
        lot_link_text = (
            "view auction",
            "browse lots",
            "view lots",
            "view lot",
        )

        for link in links:
            text = self.clean_text(link.css("::text").get()).lower()
            href = link.css("::attr(href)").get()
            if any(marker in text for marker in lot_link_text) and self.is_catalog_link(href):
                return href

        for link in links:
            href = link.css("::attr(href)").get()
            if self.is_catalog_link(href):
                return href

        return None

    def is_catalog_link(self, href: str | None) -> bool:
        if not href:
            return False

        lower_href = href.lower()
        if (
            ".pdf" in lower_href
            or "calameo.com" in lower_href
            or "image.invaluable.com" in lower_href
        ):
            return False

        path = urlsplit(href).path.lower()
        return "auction-catalog" in path
    
    def parse_auction_page(self, response):
        progress = self.progress()
        auction_id = response.meta.get("auction_id", None)
        if auction_id:
            progress.mark_started(auction_id)

        lots = response.css("div.row.lot-container > div")
        current_page = self.extract_page_number(response.url)
        next_page_url = self.extract_next_catalog_page_url(response, current_page)
        has_next_page = bool(next_page_url)
        page_numbers = self.extract_catalog_page_numbers(response)
        total_pages = max(page_numbers) if page_numbers else current_page

        if not lots and self.should_retry_empty_catalog_page(response, page_numbers, has_next_page):
            retry_count = response.meta.get("catalog_empty_retries", 0)
            if retry_count < 2:
                self.logger.warning(
                    "Retrying empty Tajan catalog page: auction_id=%s page=%s retry=%s url=%s",
                    auction_id,
                    current_page,
                    retry_count + 1,
                    response.url,
                )
                yield scrapy.Request(
                    url=response.url,
                    callback=self.parse_auction_page,
                    errback=self.parse_catalog_error,
                    meta=self.catalog_playwright_meta({
                        "auction_id": auction_id,
                        "catalog_empty_retries": retry_count + 1,
                    }),
                    dont_filter=True,
                )
                return

        for lot in lots:
            lot_item = self.build_lot_item_from_listing(lot, auction_id, response)
            if not lot_item:
                continue

            listing_result = self.parse_lot_from_listing_when_confident(lot_item)
            if listing_result:
                producers, vintages = listing_result
                progress.record_listing_only(auction_id)
                yield from self.yield_lot_with_detail_items(lot_item, producers, vintages)
                continue

            progress.record_detail_request(auction_id)
            yield response.follow(
                url=lot_item["url"],
                callback=self.parse_lot_detail,
                errback=self.parse_lot_detail_error,
                meta=self.curl_cffi_detail_meta(
                    {
                        "auction_id": auction_id,
                        "lot_item": lot_item,
                    },
                    referer=response.url,
                )
            )

        if auction_id:
            progress.record_catalog_page(
                auction_id,
                page_url=response.url,
                page_lots=len(lots),
                current_page=current_page,
                total_pages=total_pages,
                has_next_page=has_next_page,
            )
            self.logger.info(progress.catalog_progress_log_line(auction_id))
            if progress.should_log_lot_progress(auction_id):
                self.logger.info(progress.auction_progress_log_line())

        if has_next_page:
            yield response.follow(
                url=next_page_url,
                callback=self.parse_auction_page,
                errback=self.parse_catalog_error,
                meta=self.catalog_playwright_meta({
                    "auction_id": auction_id
                })
            )

    def should_retry_empty_catalog_page(self, response, page_numbers: list[int], has_next_page: bool) -> bool:
        if not self.is_catalog_link(response.url):
            return False
        if response.css("div.row.lot-container > div"):
            return False
        if has_next_page or page_numbers:
            return True
        return bool(response.css("div#catLotCountInfoM::text").get())

    def build_lot_item_from_listing(self, lot, auction_id, response):
        lot_title = self.clean_text(lot.css("h2.lot-title-block a::text").get())
        if not lot_title:
            self.logger.warning(f"Skipping Tajan lot without title on {response.url}")
            return None

        lot_id, lot_name = self.split_lot_title(lot_title)

        lot_item = LotItem()
        lot_item["auction_id"] = f"{auction_id}"
        lot_item["external_id"] = build_lot_external_id(auction_id, lot_id)
        lot_item["lot_name"] = lot_name
        lot_item["lot_type"] = ["Wine & Spirits"]

        estimate_info = self.clean_text(lot.css("p.lot-estimate::text").get())
        estimate_amount = estimate_info.split(":", 1)[1].strip() if ":" in estimate_info else estimate_info
        currency = symbol_to_currency(estimate_amount[0]) if estimate_amount else None
        lot_item["original_currency"] = currency

        price_info_element = lot.css("div.realized.mb-2")
        price_info = self.clean_text(price_info_element.css("span::text").get())
        lot_item["end_price"] = float(remove_commas(price_info[1:])) if price_info else None

        low_estimate, high_estimate = extract_price_range(estimate_amount) if estimate_amount else (None, None)
        lot_item["low_estimate"] = low_estimate
        lot_item["high_estimate"] = high_estimate
        lot_item["sold"] = lot_item["end_price"] is not None and lot_item["end_price"] > 0
        lot_item["success"] = True

        url = lot.css("h2.lot-title-block a::attr(href)").get()
        lot_item["url"] = self.normalize_lot_url(response, url)
        self.apply_volume_from_lot_name(lot_item, lot_name)

        return lot_item

    def parse_lot_detail(self, response):
        lot_item = response.meta["lot_item"]
        auction_id = response.meta.get("auction_id") or lot_item.get("auction_id")
        detail_text = self.extract_lot_detail_text(response)

        if not detail_text:
            self.logger.warning(f"No Tajan lot detail text found for {response.url}")
            self.progress().record_fallback(auction_id)
            self.log_lot_progress_if_needed(auction_id)
            yield from self.yield_lot_from_listing_only(lot_item)
            return

        parser = getattr(self, "lot_detail_parser", None)
        if parser is None:
            parser = TajanLotDetailParser()
        parsed_detail = parser.parse_detail_text(detail_text)
        if parsed_detail.description:
            lot_item["lot_name"] = parsed_detail.description
            self.apply_volume_from_lot_name(lot_item, parsed_detail.description)

        producers = list(parsed_detail.producer_candidates)
        vintages = list(parsed_detail.vintages) or extract_years(lot_item["lot_name"])
        self.apply_lwin_geography(lot_item, parsed_detail.match_text or lot_item["lot_name"])
        self.progress().record_detail_success(auction_id)
        self.log_lot_progress_if_needed(auction_id)

        yield from self.yield_lot_with_detail_items(lot_item, producers, vintages)

    def parse_lot_from_listing_when_confident(self, lot_item):
        vintages = extract_years(lot_item["lot_name"])
        if not vintages:
            return None

        try:
            lot_producer, region, sub_region, country = match_lot_info(
                lot_item["lot_name"],
                self.lwin_df,
                throw_exception=False,
            )
        except Exception as e:
            self.logger.warning(f"Tajan listing LWIN pre-check failed: {e}")
            return None

        if not lot_producer:
            return None

        if not self.producer_appears_in_title(lot_producer, lot_item["lot_name"]):
            return None

        lot_item["region"] = region
        lot_item["sub_region"] = sub_region
        lot_item["country"] = country
        return [lot_producer], vintages

    def parse_lot_detail_error(self, failure):
        lot_item = failure.request.meta.get("lot_item")
        if not lot_item:
            return

        auction_id = failure.request.meta.get("auction_id") or lot_item.get("auction_id")
        self.progress().record_detail_error(auction_id)
        self.progress().record_fallback(auction_id)
        self.log_lot_progress_if_needed(auction_id)
        self.logger.warning(f"Falling back to Tajan listing-only lot parse: {failure.value}")
        yield from self.yield_lot_from_listing_only(lot_item)

    def parse_catalog_error(self, failure):
        auction_id = failure.request.meta.get("auction_id")
        if auction_id:
            self.progress().mark_failed(auction_id)
            self.logger.warning(
                "Tajan catalog request failed: auction_id=%s url=%s error=%s",
                auction_id,
                failure.request.url,
                failure.value,
            )
            self.logger.info(self.progress().auction_progress_log_line())

    def yield_lot_from_listing_only(self, lot_item):
        producers = []
        vintages = extract_years(lot_item["lot_name"])

        try:
            lot_producer, region, sub_region, country = match_lot_info(
                lot_item["lot_name"],
                self.lwin_df,
                throw_exception=False,
            )
        except Exception as e:
            self.logger.warning(f"Tajan listing-only LWIN match failed: {e}")
        else:
            producers = [lot_producer] if lot_producer else []
            lot_item["region"] = region
            lot_item["sub_region"] = sub_region
            lot_item["country"] = country

        yield from self.yield_lot_with_detail_items(lot_item, producers, vintages)

    def yield_lot_with_detail_items(self, lot_item, producers, vintages):
        yield lot_item

        _, unit_format, _ = self.extract_volume_from_lot_name(lot_item.get("lot_name"))
        unit_formats = [unit_format] if unit_format else []
        lot_detail_items = expand_to_lot_items(producers, vintages, unit_formats, [])
        for lot_detail_item in lot_detail_items:
            lot_detail_item["lot_id"] = lot_item["external_id"]
            yield lot_detail_item

    def apply_volume_from_lot_name(self, lot_item, lot_name: str | None) -> None:
        unit, unit_format, volume = self.extract_volume_from_lot_name(lot_name)
        if unit is None or unit_format is None or volume is None:
            return
        lot_item["unit"] = unit
        lot_item["volume"] = volume

    def extract_volume_from_lot_name(self, lot_name: str | None) -> tuple[int | None, str | None, int | None]:
        text = self.clean_text(lot_name).lower()
        patterns = (
            (
                r"\b(?:ensemble\s+de\s+)?(\d+)\s*(?:bouteilles?|btlles?|btles?|btls?|btl)\b",
                "bottle",
                750,
            ),
            (r"\b(\d+)\s*magnums?\b", "magnum", 1500),
            (r"\b(\d+)\s*double[-\s]?magnums?\b", "double-magnum", 3000),
            (r"\b(\d+)\s*j[ée]roboams?\b", "jeroboam", 3000),
            (r"\b(\d+)\s*demi[-\s]?litres?\b", "500ml", 500),
            (r"\b(\d+)\s*flacons?\b", "bottle", 750),
        )

        for pattern, unit_format, volume_per_unit in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                unit = int(match.group(1))
                return unit, unit_format, unit * volume_per_unit

        return None, None, None

    def apply_lwin_geography(self, lot_item, match_text):
        try:
            _, region, sub_region, country = match_lot_info(
                match_text,
                self.lwin_df,
                throw_exception=False,
            )
        except Exception as e:
            self.logger.warning(f"Tajan detail LWIN geography match failed: {e}")
            return

        lot_item["region"] = region
        lot_item["sub_region"] = sub_region
        lot_item["country"] = country

    def extract_lot_detail_text(self, response):
        text_nodes = response.css("div.lot-info.border-bottom ::text").getall()
        if not text_nodes:
            text_nodes = response.css("div.lot-info ::text").getall()
        return self.clean_text(" ".join(text_nodes))

    def split_lot_title(self, lot_title: str) -> tuple[str, str]:
        lot_id, separator, lot_name = lot_title.partition(": ")
        if separator:
            return lot_id.strip(), lot_name.strip()
        return lot_title.strip(), lot_title.strip()

    def normalize_lot_url(self, response, url: str | None) -> str:
        if not url:
            return response.url

        absolute_url = response.urljoin(url)
        return absolute_url.replace(
            "https://www.tajan.com/auction-lot/",
            "https://www.tajan.com/en/auction-lot/",
        )

    def build_catalog_url(self, auction_link: str, page_num: int | str | None = 1) -> str:
        parts = urlsplit(auction_link)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query["displayNum"] = "180"
        if page_num is not None:
            query["pageNum"] = str(page_num)
        elif "pageNum" not in query:
            query["pageNum"] = "1"
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ))

    def extract_catalog_page_numbers(self, response) -> list[int]:
        page_numbers = []
        for href in response.css("ol.pagination.justify-content-center a::attr(href)").getall():
            page_number = self.extract_page_number(href)
            if page_number is not None:
                page_numbers.append(page_number)
        return page_numbers

    def extract_next_catalog_page_url(self, response, current_page: int | None) -> str | None:
        current_page = current_page or 1
        candidates = []
        for href in response.css("ol.pagination.justify-content-center a::attr(href)").getall():
            absolute_url = href if urlsplit(href).scheme else response.urljoin(href)
            if not self.is_catalog_link(absolute_url):
                continue

            page_number = self.extract_page_number(absolute_url)
            if page_number is not None and page_number > current_page:
                candidates.append((page_number, self.build_catalog_url(absolute_url, page_num=page_number)))

        if not candidates:
            return None
        return min(candidates, key=lambda candidate: candidate[0])[1]

    def schedule_discovered_auctions(self, response):
        progress = self.progress()
        for auction_id, (auction_item, auction_url) in self.discovered_auctions().items():
            if self.should_skip_existing_auction(auction_id, self.auction_client):
                progress.mark_skipped(auction_id)
                self.logger.info(
                    "Tajan progress: skipped complete auction auction_id=%s title=%r",
                    auction_id,
                    auction_item.get("auction_title"),
                )
                self.logger.info(progress.auction_progress_log_line())
                continue

            progress.mark_queued(auction_id)
            self.logger.info(
                "Tajan progress: queued auction auction_id=%s title=%r url=%s",
                auction_id,
                auction_item.get("auction_title"),
                auction_url,
            )
            self.logger.info(progress.auction_progress_log_line())
            yield auction_item
            yield response.follow(
                auction_url,
                self.enter_auction_page,
                errback=self.parse_catalog_error,
                meta=self.playwright_meta({
                    "auction_id": auction_id
                })
            )

    def progress(self) -> TajanProgressTracker:
        if not hasattr(self, "progress_tracker"):
            self.progress_tracker = TajanProgressTracker()
        return self.progress_tracker

    def discovered_auctions(self):
        if not hasattr(self, "discovered_auction_items"):
            self.discovered_auction_items = {}
        return self.discovered_auction_items

    def target_auction_ids(self) -> set[str]:
        if not hasattr(self, "backfill_auction_ids"):
            self.backfill_auction_ids = set()
        return self.backfill_auction_ids

    def log_lot_progress_if_needed(self, auction_id: str | None) -> None:
        if not auction_id:
            return
        progress = self.progress()
        if progress.should_log_lot_progress(auction_id):
            self.logger.info(progress.catalog_progress_log_line(auction_id))
            self.logger.info(progress.auction_progress_log_line())

    def extract_page_number(self, url: str | None) -> int | None:
        if not url:
            return None
        query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
        page_num = query.get("pageNum")
        if page_num is None:
            return None
        try:
            return int(page_num)
        except ValueError:
            return None

    def closed(self, reason):
        self.logger.info(self.progress().summary_log_line(reason))

    def producer_appears_in_title(self, producer: str | None, title: str | None) -> bool:
        producer_tokens = self.significant_tokens(producer)
        if not producer_tokens:
            return False

        title_tokens = set(self.significant_tokens(title, keep_generic=True))
        return all(token in title_tokens for token in producer_tokens)

    def significant_tokens(self, text: str | None, keep_generic: bool = False) -> list[str]:
        normalized = unicodedata.normalize("NFKD", text or "")
        normalized = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )
        normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).lower()
        tokens = [token for token in normalized.split() if token]
        if keep_generic:
            return tokens

        generic_tokens = {
            "chateau",
            "domaine",
            "de",
            "des",
            "du",
            "la",
            "le",
            "les",
            "the",
        }
        return [token for token in tokens if token not in generic_tokens]

    def clean_text(self, text: str | None) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def playwright_meta(self, extra: dict | None = None) -> dict:
        context_name, context_kwargs = self.next_playwright_context_spec()
        meta = {
            "allow_offsite": True,
            "playwright": True,
            "playwright_context": context_name,
            "playwright_page_goto_kwargs": {
                "wait_until": "domcontentloaded",
                "timeout": 30000,
            },
        }
        if context_kwargs:
            meta["playwright_context_kwargs"] = context_kwargs
        if extra:
            meta.update(extra)
        return meta

    def build_playwright_context_specs(self) -> tuple[tuple[str, dict | None], ...]:
        proxy_contexts = build_tajan_proxy_contexts()
        if not proxy_contexts:
            return (("tajan", None),)
        return tuple(proxy_contexts.items())

    def next_playwright_context_spec(self) -> tuple[str, dict | None]:
        if hasattr(self, "playwright_context_specs"):
            specs = self.playwright_context_specs
        elif hasattr(self, "playwright_context_names"):
            specs = tuple((name, None) for name in self.playwright_context_names)
        else:
            specs = (("tajan", None),)
            self.playwright_context_specs = specs

        if os.getenv("TAJAN_PROXY_ROTATION", "").strip().lower() != "request":
            return specs[0]

        index = getattr(self, "_playwright_context_index", 0)
        context_name, context_kwargs = specs[index % len(specs)]
        self._playwright_context_index = index + 1
        return context_name, context_kwargs

    def catalog_playwright_meta(self, extra: dict | None = None) -> dict:
        meta = self.playwright_meta(extra)
        wait_ms = int(os.getenv("TAJAN_CATALOG_WAIT_MS", "2000"))
        meta["playwright_page_methods"] = [
            PageMethod("wait_for_timeout", wait_ms),
        ]
        return meta

    def curl_cffi_detail_meta(self, extra: dict | None = None, referer: str | None = None) -> dict:
        meta = {
            "allow_offsite": True,
            "curl_cffi": True,
            "dont_retry": True,
        }
        if referer:
            meta["curl_cffi_referer"] = referer
        if extra:
            meta.update(extra)
        return meta
    
    def extract_raw_dates_from_event_date(self, text: str) -> list[str]:
        pattern = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Za-z]+\s+\d{1,2},\s+\d{4}"
        return re.findall(pattern, text)
