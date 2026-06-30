import os
import json
import scrapy
import dotenv
import asyncio
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from playwright.sync_api import sync_playwright
from wine_spider.services import ZachysClient
from wine_spider.helpers import (
    AUCTION_LANDING_URL,
    build_zachys_categories_url,
    extract_zachys_lot_count_from_categories,
    extract_zachys_past_catalog_links,
)
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")
DEFAULT_ZACHYS_REPORT_MAX_PAGES = 3

ZACHYS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )
}

ZACHYS_XHR_HEADERS = {
    **ZACHYS_HEADERS,
    "accept": "application/json, text/javascript, */*; q=0.01",
    "x-requested-with": "XMLHttpRequest",
}


def fetch_text(url: str, headers: dict | None = None, timeout: int = 30) -> str:
    response = cffi_requests.get(
        url,
        impersonate="chrome142",
        headers=headers or ZACHYS_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def build_zachys_auction_list_url(page: int, status: int = 5) -> str:
    return f"https://bid.zachys.com/auctions?page={page}&status={status}"


def build_zachys_catalog_url(auction_id: str | int, auction_seo_name: str) -> str:
    return f"https://bid.zachys.com/auctions/catalog/id/{auction_id}/{auction_seo_name}"


def extract_zachys_auction_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"data-server": True}):
        text = script.get_text()
        if "auctionRows" not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        return (data.get("default") or {}).get("auctionRows") or []
    return []


def fetch_zachys_past_auction_rows(max_pages: int | None = None) -> list[dict]:
    max_pages = max_pages or int(
        os.getenv("ZACHYS_REPORT_MAX_PAGES", str(DEFAULT_ZACHYS_REPORT_MAX_PAGES))
    )
    rows: list[dict] = []
    seen_ids: set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=ZACHYS_HEADERS["User-Agent"],
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        try:
            for page_number in range(1, max_pages + 1):
                url = build_zachys_auction_list_url(page_number, status=5)
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                page.wait_for_timeout(8_000)
                page_rows = extract_zachys_auction_rows(page.content())
                print(f"Loaded Zachys past listing page {page_number}: {len(page_rows)} auctions")
                if not page_rows:
                    break

                new_rows = 0
                for row in page_rows:
                    auction_id = str(row.get("id") or "").strip()
                    if not auction_id or auction_id in seen_ids:
                        continue
                    seen_ids.add(auction_id)
                    rows.append(row)
                    new_rows += 1

                if new_rows == 0:
                    break
        finally:
            browser.close()

    return rows


def fetch_zachys_landing_category_rows() -> list[dict]:
    landing_html = fetch_text(AUCTION_LANDING_URL)
    catalog_links = extract_zachys_past_catalog_links(landing_html)
    rows = []
    for catalog in catalog_links:
        category_json = fetch_text(
            build_zachys_categories_url(catalog.auction_id),
            headers={**ZACHYS_XHR_HEADERS, "referer": catalog.catalog_url},
        )
        rows.append(
            {
                "id": catalog.auction_id,
                "name": catalog.title,
                "auction_seo_url": catalog.auction_seo_name,
                "total_lots": extract_zachys_lot_count_from_categories(
                    json.loads(category_json)
                ),
            }
        )
    return rows


def run_report() -> None:
    report = AuctionScrapingReportGenerator("Zachys")
    lot_counts_by_id = {
        row["external_id"]: row for row in report.load_lot_counts_from_db()
    }

    auction_rows = fetch_zachys_past_auction_rows()
    if not auction_rows:
        print("Zachys past listing returned no auctionRows; falling back to auction landing page")
        auction_rows = fetch_zachys_landing_category_rows()

    print(f"Found {len(auction_rows)} Zachys past auctions")

    for auction in auction_rows:
        auction_id = str(auction.get("id") or "").strip()
        if not auction_id:
            continue

        external_id = f"zachys_{auction_id}"
        print(f"Processing auction: {external_id} - {auction.get('name')}")
        try:
            hits = int(auction.get("total_lots") or 0)
        except (TypeError, ValueError):
            hits = 0

        auction_url = build_zachys_catalog_url(
            auction_id,
            auction.get("auction_seo_url") or "",
        )
        existing = lot_counts_by_id.get(external_id)

        if existing:
            lot_count = existing["lot_count"]
            url = existing["url"]
        else:
            lot_count = 0
            url = auction_url

        report.add_result(
            external_id=external_id,
            hits=hits,
            lot_count=lot_count,
            match=lot_count == hits,
            url=url,
        )

    report.export()

class ZachysReportSpider(scrapy.Spider):
    name = "zachys_report_spider"
    allowed_domains = [
        "auction.zachys.com",
        "bid.zachys.com",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": build_spider_log_file("zachys_report.log"),
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 5,
        "DOWNLOAD_TIMEOUT": 90,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "DOWNLOADER_MIDDLEWARES": {
            "wine_spider.middlewares.aws_waf_bypass.AwsWafBypassMiddleware": 543,
        },
        
        "AWS_WAF_MAX_RETRIES": 2,
        "AWS_WAF_MIN_DELAY": 3000,
        "AWS_WAF_MAX_DELAY": 3000,
        "AWS_WAF_RETRY_BASE_DELAY": 30,
        "AWS_WAF_RETRY_MAX_DELAY": 180,
        "AWS_WAF_CLOSE_SPIDER_ON_BLOCK": True,
        "AWS_WAF_COOKIES_FILE": "wine_spider.login_state.zachys_cookies.json",
        "AWS_WAF_TOKENS_FILE": "wine_spider.login_state.zachys_tokens.json",
        "AWS_WAF_ENABLED_SPIDERS": ["zachys_spider", "zachys_report_spider"],
        
        "PLAYWRIGHT_CONTEXTS": {
            "zachys": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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
                    "Cache-Control": "max-age=0"
                },
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False,
                "bypass_csp": True
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super(ZachysReportSpider, self).__init__(*args, **kwargs)
        self.zachys_client = ZachysClient()
        self.report = AuctionScrapingReportGenerator("Zachys")
        self.lot_counts_from_db = self.report.load_lot_counts_from_db()

        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    def start_requests(self):
        yield scrapy.Request(
            url=AUCTION_LANDING_URL,
            callback=self.parse,
            dont_filter=True,
        )
        print(f"Requesting Zachys auction landing page: {AUCTION_LANDING_URL}")

    def parse(self, response):
        catalog_links = extract_zachys_past_catalog_links(response.text)
        print(f"Found {len(catalog_links)} Zachys past auction catalog links")

        for catalog in catalog_links:
            external_id = f"zachys_{catalog.auction_id}"
            print(f"Processing auction: {external_id} - {catalog.title}")
            yield scrapy.Request(
                url=build_zachys_categories_url(catalog.auction_id),
                callback=self.add_results,
                headers={
                    "accept": "application/json, text/javascript, */*; q=0.01",
                    "referer": catalog.catalog_url,
                    "x-requested-with": "XMLHttpRequest",
                },
                meta={
                    "auction_id": external_id,
                    "auction_url": catalog.catalog_url,
                },
                dont_filter=True,
            )
    
    def add_results(self, response):
        auction_id = response.meta.get("auction_id")
        auction_url = response.meta.get("auction_url", response.url)
        
        try:
            hits = extract_zachys_lot_count_from_categories(json.loads(response.text))

            found = False
            for lot in self.lot_counts_from_db:
                if lot["external_id"] == auction_id:
                    lot_count = lot["lot_count"]
                    url = lot["url"]
                    match = lot_count == hits
                    found = True
                    self.report.add_result(
                        external_id=auction_id,
                        hits=hits,
                        lot_count=lot_count,
                        match=match,
                        url=url
                    )

                    break

            if not found:
                self.report.add_result(
                    external_id=auction_id,
                    hits=hits,
                    lot_count=0,
                    match=False,
                    url=auction_url
                )

        except Exception as e:
            print(f"Error fetching Zachys category count: {e}")

    def closed(self, reason):
        self.report.export()
