import json
import os
import re
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from wine_spider.helpers.wineauctioneer.login import get_chrome_executable_path
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator


BASE_URL = "https://wineauctioneer.com"
PAST_AUCTIONS_URL = f"{BASE_URL}/wine-auctions"
COOKIE_STATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "login_state"
    / "wineauctioneer_cookies.json"
)


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


def cookies_from_storage_state(storage_state: dict) -> dict[str, str]:
    return {
        cookie["name"]: cookie["value"]
        for cookie in storage_state.get("cookies", [])
        if cookie.get("name") and cookie.get("value") is not None
    }


def load_cookies(path: str | Path = COOKIE_STATE_PATH) -> dict[str, str]:
    cookie_path = Path(path)
    if not cookie_path.exists():
        return {}
    return cookies_from_storage_state(json.loads(cookie_path.read_text(encoding="utf-8")))


def env_truthy(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def playwright_cookies(cookies: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "name": name,
            "value": value,
            "domain": ".wineauctioneer.com" if name.startswith("_") else "wineauctioneer.com",
            "path": "/",
        }
        for name, value in cookies.items()
    ]


class BrowserHtmlFetcher:
    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        launch_options = {
            "headless": env_truthy("WINEAUCTIONEER_BROWSER_HEADLESS", True),
        }
        chrome_path = get_chrome_executable_path()
        if chrome_path:
            launch_options["executable_path"] = chrome_path
        self.browser = self.playwright.chromium.launch(**launch_options)
        self.context = self.browser.new_context(
            user_agent=navigation_headers()["user-agent"],
            extra_http_headers={
                key: value
                for key, value in navigation_headers().items()
                if key not in {"user-agent", "referer"}
            },
        )
        if self.cookies:
            self.context.add_cookies(playwright_cookies(self.cookies))
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def fetch(self, url: str, referer: str | None = None) -> str | None:
        response = None
        try:
            response = self.page.goto(
                url,
                wait_until="domcontentloaded",
                referer=referer,
                timeout=45000,
            )
        except PlaywrightError:
            response = None
        if response and response.status == 200:
            return self.page.content()

        clicked_html = self._fetch_by_clicking(url, referer)
        if clicked_html:
            return clicked_html

        status = response.status if response else None
        print(f"Browser fallback failed to fetch {url}: {status}")
        return None

    def _fetch_by_clicking(self, url: str, referer: str | None) -> str | None:
        if not referer:
            return None

        target_path = urlparse(url).path.lower()
        listing_url = referer
        for page_number in range(0, 8):
            if page_number == 0:
                page_url = listing_url
            else:
                page_url = f"{listing_url}?page=0%2C{page_number}%2C0%2C0%2C0#past-auctions"
            try:
                self.page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
            except PlaywrightError:
                continue
            match_indexes = self.page.locator("a[href]").evaluate_all(
                """
                (links, targetPath) => links
                    .map((link, index) => {
                        try {
                            return {
                                index,
                                path: new URL(link.href, window.location.href).pathname.toLowerCase(),
                            };
                        } catch {
                            return null;
                        }
                    })
                    .filter((link) => link && link.path === targetPath)
                    .map((link) => link.index)
                """,
                target_path,
            )
            if not match_indexes:
                continue
            try:
                with self.page.expect_response(
                    lambda resp: urlparse(resp.url).path.lower() == target_path,
                    timeout=45000,
                ) as response_info:
                    self.page.locator("a[href]").nth(match_indexes[0]).click()
                response = response_info.value
                self.page.wait_for_load_state("domcontentloaded", timeout=45000)
                if response.status == 200:
                    return self.page.content()
            except (PlaywrightError, PlaywrightTimeoutError):
                continue
        return None


def fetch_html(
    url: str,
    cookies: dict[str, str],
    referer: str | None = None,
    browser_fetcher: BrowserHtmlFetcher | None = None,
) -> str | None:
    try:
        response = cffi_requests.get(
            url,
            cookies=cookies,
            headers=navigation_headers(referer),
            impersonate="chrome124",
            timeout=30,
        )
        if response.status_code != 200:
            if response.status_code == 406 and browser_fetcher:
                html = browser_fetcher.fetch(url, referer=referer)
                if html:
                    return html
            print(f"Failed to fetch {url}: {response.status_code}")
            return None
        return response.text
    except Exception as exc:
        print(f"Failed to fetch {url}: {exc}")
        return None


def extract_listing_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    auction_links = soup.select("a.btn[href*='/wine-auctions/'][href$='/lots']")
    return [link["href"] for link in auction_links if link.get("href")]


def extract_pagination_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for link in soup.select("a[href*='page=']"):
        href = link.get("href")
        if href and "0%2C0%2C0%2C0%2C0" not in href and "0,0,0,0,0" not in href:
            urls.append(urljoin(f"{BASE_URL}/wine-auctions", href))
    return urls


def extract_hits(html: str) -> tuple[int, str] | None:
    soup = BeautifulSoup(html, "html.parser")
    span = soup.find("span", class_="result-summary")
    title = soup.find("h1", class_="page-title")
    if not span or not title:
        return None

    external_id = title.get_text(strip=True).replace(" ", "-").lower()
    match = re.search(r"(\d+)\s*-\s*(\d+)\s*of\s*(\d+)\s*Lots", span.get_text(strip=True))
    if not match:
        return None

    return int(match.group(3)), external_id


def main():
    report = AuctionScrapingReportGenerator("Wineauctioneer")
    auction_lots_data = report.load_lot_counts_from_db()
    auction_lots_by_id = {
        row["external_id"]: row
        for row in auction_lots_data
    }
    cookies = load_cookies()
    use_browser_fallback = env_truthy("WINEAUCTIONEER_BROWSER_FALLBACK", True)

    with BrowserHtmlFetcher(cookies) if use_browser_fallback else nullcontext() as browser_fetcher:
        initial_urls = [PAST_AUCTIONS_URL]
        all_urls = []
        visited_listing_pages = set()
        for url in initial_urls:
            html = fetch_html(url, cookies, referer=BASE_URL, browser_fetcher=browser_fetcher)
            if not html:
                continue
            visited_listing_pages.add(url)
            all_urls.extend(extract_listing_urls(html))
            for page_url in extract_pagination_urls(html):
                if page_url in visited_listing_pages:
                    continue
                visited_listing_pages.add(page_url)
                page_html = fetch_html(
                    page_url,
                    cookies,
                    referer=PAST_AUCTIONS_URL,
                    browser_fetcher=browser_fetcher,
                )
                if page_html:
                    all_urls.extend(extract_listing_urls(page_html))

        for path in sorted(set(all_urls)):
            url = path if path.startswith("http") else f"{BASE_URL}{path}"
            html = fetch_html(
                url,
                cookies,
                referer=PAST_AUCTIONS_URL,
                browser_fetcher=browser_fetcher,
            )
            if not html:
                continue
            result = extract_hits(html)
            if not result:
                continue

            total, external_id = result
            auction = auction_lots_by_id.get(external_id)
            if auction:
                lot_count = auction["lot_count"]
                report_url = auction["url"]
            else:
                lot_count = 0
                report_url = url

            report.add_result(
                external_id=external_id,
                hits=total,
                lot_count=lot_count,
                match=total == lot_count,
                url=report_url,
            )

    report.export()


if __name__ == "__main__":
    main()
