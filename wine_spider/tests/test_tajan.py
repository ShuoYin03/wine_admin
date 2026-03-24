from __future__ import annotations

import re
import unittest

from playwright.sync_api import sync_playwright
from scrapy.http import HtmlResponse

PAST_AUCTIONS_URL = "https://www.tajan.com/en/past/"


def playwright_get(url: str, timeout_ms: int = 30_000) -> HtmlResponse:
    """Render a page with Playwright (headless Chromium) and return an HtmlResponse.

    Raises SkipTest if Cloudflare or another bot-protection layer blocks the request.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            # Wait for the results container to appear (JS-rendered)
            try:
                page.wait_for_selector("#plab__results-container", timeout=10_000)
            except Exception:
                pass  # Still try to parse whatever loaded
            html = page.content()
        finally:
            browser.close()

    # Detect Cloudflare block page
    if "Attention Required! | Cloudflare" in html or "have been blocked" in html:
        raise unittest.SkipTest(
            "Tajan.com is protected by Cloudflare and blocks headless Playwright. "
            "The production spider uses a persistent Playwright browser context with "
            "saved cookies/state that bypasses this. "
            "Run the spider with `scrapy crawl tajan_spider` to verify."
        )

    return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8")


class TestTajanPastAuctionsPage(unittest.TestCase):
    """Verify the Tajan past-auctions listing page is still parseable."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.response = playwright_get(PAST_AUCTIONS_URL)
        except Exception as e:
            raise unittest.SkipTest(f"Tajan past-auctions page unreachable: {e}")

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_results_container_exists(self):
        container = self.response.css("div#plab__results-container")
        self.assertIsNotNone(
            container.get(),
            "Selector 'div#plab__results-container' returned nothing — "
            "Tajan may have changed their page structure",
        )

    def test_auction_events_found(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        self.assertGreater(
            len(events), 0,
            "No auction events found via 'div.widget-event' — "
            "page structure may have changed",
        )

    def test_auction_title_extractable(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        for event in events[:3]:
            title = event.css("h2.event__title a::text").get()
            self.assertIsNotNone(
                title, "Selector 'h2.event__title a::text' returned None"
            )
            self.assertNotEqual(title.strip(), "")

    def test_auction_date_extractable(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        for event in events[:3]:
            date = event.css("div.event__date::text").get()
            self.assertIsNotNone(
                date, "Selector 'div.event__date::text' returned None"
            )

    def test_auction_location_extractable(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        for event in events[:3]:
            location = event.css("div.event__location.mb-0::text").get()
            self.assertIsNotNone(
                location, "Selector 'div.event__location.mb-0::text' returned None"
            )

    def test_auction_url_extractable(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        for event in events[:3]:
            url = event.css("h2.event__title a::attr(href)").get()
            self.assertIsNotNone(url, "Auction URL selector returned None")
            self.assertIn("/tajan.com/", url, f"Unexpected auction URL format: {url}")

    def test_wine_auction_present(self):
        events = self.response.css("div#plab__results-container div.widget-event")
        titles = [
            (e.css("h2.event__title a::text").get() or "").lower()
            for e in events
        ]
        wine_events = [t for t in titles if "wine" in t or "spirits" in t or "vins" in t]
        self.assertGreater(
            len(wine_events), 0,
            f"No wine/spirits events found among {len(titles)} events — "
            "the listing may only show non-wine auctions",
        )


class TestTajanAuctionPage(unittest.TestCase):
    """Verify a Tajan auction detail page (lot-listing page) is still parseable."""

    @classmethod
    def setUpClass(cls):
        # Get a wine auction URL from the listing
        try:
            listing = playwright_get(PAST_AUCTIONS_URL)
        except Exception as e:
            raise unittest.SkipTest(f"Tajan listing unreachable: {e}")

        events = listing.css("div#plab__results-container div.widget-event")
        wine_url = None
        for event in events:
            title = (event.css("h2.event__title a::text").get() or "").lower()
            if "wine" in title or "spirits" in title or "vins" in title:
                wine_url = event.css("h2.event__title a::attr(href)").get()
                break

        if wine_url is None:
            raise unittest.SkipTest("No wine/spirits auction found on listing page")

        # The auction detail page may link to the lot listing via div.sale-ctas
        try:
            detail_page = playwright_get(wine_url)
        except Exception as e:
            raise unittest.SkipTest(f"Tajan auction detail page unreachable: {e}")

        # Find the lot listing link
        lot_list_url = None
        for a in detail_page.css("div.sale-ctas a"):
            text = (a.css("::text").get() or "").lower()
            href = a.css("::attr(href)").get() or ""
            if any(kw in text for kw in ("view auction", "browse lots", "view lots", "view lot")):
                lot_list_url = href
                break
        if lot_list_url is None:
            # Fall back to first link in sale-ctas that isn't calameo
            for a in detail_page.css("div.sale-ctas a"):
                href = a.css("::attr(href)").get() or ""
                if "calameo.com" not in href:
                    lot_list_url = href
                    break

        if lot_list_url:
            try:
                cls.response = playwright_get(
                    f"{lot_list_url}?displayNum=180&pageNum=1"
                )
                cls.source = "lot_list"
            except Exception as e:
                raise unittest.SkipTest(f"Tajan lot list page unreachable: {e}")
        else:
            # Use the detail page itself as fallback
            cls.response = detail_page
            cls.source = "detail"

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_lot_container_exists(self):
        lots = self.response.css("div.row.lot-container > div")
        if self.source == "detail":
            self.skipTest("Using auction detail page (no lot-container found) — no lots URL available")
        self.assertGreater(
            len(lots), 0,
            "Selector 'div.row.lot-container > div' returned no lots — "
            "page structure may have changed",
        )

    def test_lot_title_extractable(self):
        lots = self.response.css("div.row.lot-container > div")
        if not lots:
            self.skipTest("No lot containers found")
        for lot in lots[:5]:
            title = lot.css("h2.lot-title-block a::text").get()
            self.assertIsNotNone(
                title, "Lot title selector 'h2.lot-title-block a::text' returned None"
            )
            self.assertNotEqual(title.strip(), "")

    def test_lot_estimate_extractable(self):
        lots = self.response.css("div.row.lot-container > div")
        if not lots:
            self.skipTest("No lot containers found")
        # Not all lots may have estimates; just check the selector works on at least one
        estimates = [
            lot.css("p.lot-estimate::text").get()
            for lot in lots[:10]
        ]
        has_estimate = any(e is not None for e in estimates)
        self.assertTrue(
            has_estimate,
            "No lot estimates found via 'p.lot-estimate::text' in first 10 lots",
        )

    def test_lot_url_extractable(self):
        lots = self.response.css("div.row.lot-container > div")
        if not lots:
            self.skipTest("No lot containers found")
        for lot in lots[:5]:
            url = lot.css("h2.lot-title-block a::attr(href)").get()
            self.assertIsNotNone(
                url, "Lot URL selector 'h2.lot-title-block a::attr(href)' returned None"
            )


if __name__ == "__main__":
    unittest.main()
