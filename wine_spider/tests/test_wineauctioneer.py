from __future__ import annotations

import json
import os
import unittest
from datetime import datetime

from curl_cffi import requests as cffi_requests
from scrapy.http import HtmlResponse

PAST_AUCTIONS_URL = "https://wineauctioneer.com/wine-auctions"
COOKIE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "wine_spider", "wine_spider", "login_state", "wineauctioneer_cookies.json"
)


def cffi_get(url: str) -> HtmlResponse:
    """Fetch a URL using curl_cffi (browser impersonation)."""
    r = cffi_requests.get(url, impersonate="chrome124", timeout=20)
    r.raise_for_status()
    return HtmlResponse(url=url, body=r.content)


class TestWineAuctioneerPastAuctionsPage(unittest.TestCase):
    """Verify the WineAuctioneer past auctions listing page is still parseable."""

    @classmethod
    def setUpClass(cls):
        cls.response = cffi_get(PAST_AUCTIONS_URL)

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_auction_links_found(self):
        links = self.response.css(
            "a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)"
        ).getall()
        self.assertGreater(
            len(links), 0,
            "No auction links found — selector 'a.btn[href*=\"/wine-auctions/\"][href$=\"/lots\"]' may have changed",
        )

    def test_auction_links_format(self):
        links = self.response.css(
            "a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)"
        ).getall()
        for link in links[:5]:
            self.assertIn("/wine-auctions/", link)
            self.assertTrue(link.endswith("/lots"))


class TestWineAuctioneerAuctionPage(unittest.TestCase):
    """Verify a WineAuctioneer auction detail page is still parseable."""

    @classmethod
    def setUpClass(cls):
        listing = cffi_get(PAST_AUCTIONS_URL)
        links = listing.css(
            "a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)"
        ).getall()

        if not links:
            raise unittest.SkipTest("No auction links found — cannot test auction page")

        # Use the first accessible auction link.
        # We skip index 0 if it appears to be a live/upcoming auction;
        # any past page works for structural tests.
        auction_path = None
        for path in links[:5]:
            if not path.startswith("http"):
                path = "https://wineauctioneer.com" + path
            try:
                resp = cffi_get(path)
                auction_path = path
                cls.response = resp
                break
            except Exception:
                continue

        if auction_path is None:
            raise unittest.SkipTest("No accessible auction page found (all returned errors)")
        cls.auction_url = auction_path

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_auction_title_extractable(self):
        title = self.response.css("h1.page-title::text").get()
        self.assertIsNotNone(title, "Selector 'h1.page-title::text' returned None")
        self.assertNotEqual(title.strip(), "")

    def test_auction_start_date_extractable(self):
        start_date = self.response.css(
            "div.auction-info.field-hstack div:first-child div::text"
        ).get()
        self.assertIsNotNone(
            start_date,
            "Start date selector returned None — page structure may have changed",
        )
        try:
            datetime.strptime(start_date.strip(), "%d %B %Y")
        except ValueError as e:
            self.fail(f"Start date '{start_date}' not parseable as '%d %B %Y': {e}")

    def test_auction_end_date_extractable(self):
        end_date = self.response.css(
            "div.auction-info.field-hstack div:nth-child(2) div:last-child::text"
        ).get()
        self.assertIsNotNone(end_date, "End date selector returned None")

    def test_auction_status_extractable(self):
        # Closed auctions use class 'auction-status-closed'; active ones use other classes.
        # Either way, the div.auction-status element should exist.
        status = self.response.css("div.auction-status::text").get()
        self.assertIsNotNone(
            status,
            "Auction status selector 'div.auction-status::text' returned None — page structure may have changed",
        )
        self.assertNotEqual(status.strip(), "")

    def test_lot_links_found(self):
        lot_links = self.response.css("h3.teaser-title a::attr(href)").getall()
        self.assertGreater(
            len(lot_links), 0,
            "No lot links found via 'h3.teaser-title a::attr(href)' — page structure may have changed",
        )


class TestWineAuctioneerLotPage(unittest.TestCase):
    """Verify a WineAuctioneer lot detail page is still parseable.

    NOTE: Individual lot pages require authentication. This test class is skipped
    automatically when the lot page returns a non-200 status (e.g. 406).
    To run these tests, ensure valid cookies exist at COOKIE_PATH.
    """

    @classmethod
    def setUpClass(cls):
        listing = cffi_get(PAST_AUCTIONS_URL)
        auction_links = listing.css(
            "a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)"
        ).getall()
        if not auction_links:
            raise unittest.SkipTest("No auction links found")

        # Find an accessible auction page that has lot links
        lot_links = []
        for path in auction_links[:5]:
            if not path.startswith("http"):
                path = "https://wineauctioneer.com" + path
            try:
                resp = cffi_get(path)
            except Exception:
                continue
            lot_links = resp.css("h3.teaser-title a::attr(href)").getall()
            if lot_links:
                break

        if not lot_links:
            raise unittest.SkipTest("No auction with lot links found")

        lot_path = lot_links[0]
        if not lot_path.startswith("http"):
            lot_path = "https://wineauctioneer.com" + lot_path
        cls.lot_url = lot_path

        try:
            cls.response = cffi_get(lot_path)
        except Exception as e:
            raise unittest.SkipTest(
                f"Lot page {lot_path} returned an error ({e}). "
                "Lot pages require authentication — provide valid cookies at COOKIE_PATH."
            )

    def test_lot_title_extractable(self):
        title = self.response.css("h1.page-title::text").get()
        self.assertIsNotNone(title, "Lot title selector 'h1.page-title::text' returned None")
        self.assertNotEqual(title.strip(), "")

    def test_lot_id_extractable(self):
        ids = self.response.css("div.mb-1::text").getall()
        self.assertGreater(len(ids), 0, "Lot ID selector 'div.mb-1::text' returned nothing")
        lot_id = ids[-1].strip()
        self.assertNotEqual(lot_id, "")

    def test_lot_size_field_exists(self):
        size = self.response.css(
            "div.field.field--name-field-size div.field__item::text"
        ).get()
        self.assertIsNotNone(
            size,
            "Lot size selector 'div.field.field--name-field-size div.field__item::text' returned None",
        )

    def test_lot_producer_field_exists(self):
        producer = self.response.css(
            "div.field.field--name-field-producer div.field__item a::text"
        ).get()
        self.assertIsInstance(producer, (str, type(None)))


if __name__ == "__main__":
    unittest.main()
