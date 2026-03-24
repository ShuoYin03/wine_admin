from __future__ import annotations

import re
import json
import unittest
from io import BytesIO

import pandas as pd
from curl_cffi import requests as cffi_requests
from scrapy.http import HtmlResponse

BASE_URL = "https://bid.zachys.com"
AUCTIONS_URL = f"{BASE_URL}/auctions?page=1&status=5"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Known Excel export columns the spider depends on
REQUIRED_EXCEL_COLUMNS = {
    "Lot", "Lot Title", "Size", "Qty",
    "Low Estimate", "High Estimate", "Producer", "Vintage",
}


def cffi_get(url: str, timeout: int = 30) -> HtmlResponse:
    """Fetch a URL with curl_cffi browser impersonation to bypass AWS WAF."""
    r = cffi_requests.get(url, impersonate="chrome124", timeout=timeout, headers=HEADERS)
    r.raise_for_status()
    return HtmlResponse(url=url, body=r.content)


def _fetch_zachys_listing() -> HtmlResponse:
    """Fetch the Zachys listing page, raising SkipTest if AWS WAF blocks it."""
    r = cffi_requests.get(
        AUCTIONS_URL, impersonate="chrome124", timeout=30, headers=HEADERS
    )
    # AWS WAF challenge pages return 202 with challenge JS — not real content
    if r.status_code == 202 or "awsWafCookieDomainList" in r.text:
        raise unittest.SkipTest(
            "Zachys listing blocked by AWS WAF challenge. "
            "The spider uses a Playwright-based WAF bypass middleware that cannot be "
            "replicated in a plain HTTP test. Run the spider directly to verify."
        )
    r.raise_for_status()
    return HtmlResponse(url=AUCTIONS_URL, body=r.content)


class TestZachysAuctionListPage(unittest.TestCase):
    """Verify the Zachys past-auctions listing page embeds the auctionRows JSON."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.response = _fetch_zachys_listing()
        except unittest.SkipTest:
            raise
        except Exception as e:
            raise unittest.SkipTest(
                f"Zachys listing page unreachable: {e}"
            )

        # Extract the auctionRows JSON the spider depends on
        match = re.search(
            r'auctionRows"\s*,\s*(\[\{.*?\}\])\);',
            cls.response.text,
            re.DOTALL,
        )
        cls.auction_rows_match = match
        try:
            cls.auction_rows = json.loads(match.group(1)) if match else None
        except Exception:
            cls.auction_rows = None

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_auction_rows_json_embedded(self):
        self.assertIsNotNone(
            self.auction_rows_match,
            "Pattern 'auctionRows' not found in page script — Zachys may have changed their JS structure",
        )

    def test_auction_rows_is_list(self):
        if self.auction_rows is None:
            self.skipTest("auctionRows JSON not found or not parseable")
        self.assertIsInstance(self.auction_rows, list)
        self.assertGreater(len(self.auction_rows), 0, "auctionRows list is empty")

    def test_auction_rows_have_required_fields(self):
        if not self.auction_rows:
            self.skipTest("auctionRows not available")
        required = {"id", "name", "start_date", "end_date", "auction_seo_url"}
        for auction in self.auction_rows[:3]:
            self.assertIsInstance(auction, dict)
            for field in required:
                self.assertIn(field, auction, f"Auction entry missing field '{field}'")

    def test_auction_ids_not_empty(self):
        if not self.auction_rows:
            self.skipTest("auctionRows not available")
        for auction in self.auction_rows[:5]:
            self.assertIsNotNone(auction.get("id"))
            self.assertNotEqual(str(auction.get("id", "")).strip(), "")


class TestZachysAuctionLotPage(unittest.TestCase):
    """Verify the Zachys lot listing page for a known auction is still parseable."""

    @classmethod
    def setUpClass(cls):
        # First, get an auction ID and seo name from the listing
        try:
            listing = _fetch_zachys_listing()
        except unittest.SkipTest:
            raise
        except Exception as e:
            raise unittest.SkipTest(f"Zachys listing unreachable: {e}")

        match = re.search(
            r'auctionRows"\s*,\s*(\[\{.*?\}\])\);',
            listing.text,
            re.DOTALL,
        )
        if not match:
            raise unittest.SkipTest("auctionRows JSON not found on listing page")

        try:
            auction_rows = json.loads(match.group(1))
        except Exception:
            raise unittest.SkipTest("auctionRows JSON not parseable")

        if not auction_rows:
            raise unittest.SkipTest("auctionRows list is empty")

        first = auction_rows[0]
        catalog_id = first.get("id")
        seo_name = first.get("auction_seo_url", "")
        lots_url = f"{BASE_URL}/auctions/catalog/id/{catalog_id}/{seo_name}?items=100&page=1"

        try:
            cls.response = cffi_get(lots_url)
        except Exception as e:
            raise unittest.SkipTest(f"Zachys lot page unreachable: {e}")

        cls.lots_url = lots_url

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_excel_download_link_or_lot_items_present(self):
        # The page should have either lot items (div.list-cols.info-col) or an Excel export link
        lot_items = self.response.css("div.list-cols.info-col")
        excel_link = self.response.css("a.excel_doc::attr(href)").get()
        self.assertTrue(
            len(lot_items) > 0 or excel_link is not None,
            "Neither lot items ('div.list-cols.info-col') nor Excel link ('a.excel_doc') found — "
            "page structure may have changed",
        )


class TestZachysExcelParsing(unittest.TestCase):
    """Verify a Zachys Excel export file has the expected columns and structure."""

    @classmethod
    def setUpClass(cls):
        # Get the listing to find a real Excel export link
        try:
            listing = _fetch_zachys_listing()
        except unittest.SkipTest:
            raise
        except Exception as e:
            raise unittest.SkipTest(f"Zachys listing unreachable: {e}")

        match = re.search(
            r'auctionRows"\s*,\s*(\[\{.*?\}\])\);',
            listing.text,
            re.DOTALL,
        )
        if not match:
            raise unittest.SkipTest("auctionRows JSON not found")

        try:
            auction_rows = json.loads(match.group(1))
        except Exception:
            raise unittest.SkipTest("auctionRows not parseable")

        if not auction_rows:
            raise unittest.SkipTest("No auctions found")

        # Find an auction lot page that has an Excel link
        excel_link = None
        for auction in auction_rows[:5]:
            catalog_id = auction.get("id")
            seo_name = auction.get("auction_seo_url", "")
            lots_url = f"{BASE_URL}/auctions/catalog/id/{catalog_id}/{seo_name}?items=100&page=1"
            try:
                lot_page = cffi_get(lots_url)
            except Exception:
                continue
            link = lot_page.css("a.excel_doc::attr(href)").get()
            if link:
                excel_link = link
                break

        if excel_link is None:
            raise unittest.SkipTest("No Excel export link found on any lot page")

        # Download the Excel file
        try:
            r = cffi_requests.get(
                excel_link, impersonate="chrome124", timeout=60, headers=HEADERS
            )
            r.raise_for_status()
            cls.excel_bytes = r.content
        except Exception as e:
            raise unittest.SkipTest(f"Excel file download failed: {e}")

        # Parse it
        try:
            cls.df = pd.read_excel(
                BytesIO(cls.excel_bytes), sheet_name="Sheet1", engine="xlrd", header=2
            )
        except Exception as e:
            raise unittest.SkipTest(f"Excel file not parseable: {e}")

    def test_excel_has_rows(self):
        self.assertGreater(len(self.df), 0, "Excel file has no data rows")

    def test_excel_has_required_columns(self):
        cols = set(self.df.columns)
        for col in REQUIRED_EXCEL_COLUMNS:
            self.assertIn(col, cols, f"Excel missing required column '{col}'. Columns: {sorted(cols)}")

    def test_lot_column_not_all_null(self):
        self.assertFalse(
            self.df["Lot"].isna().all(),
            "'Lot' column is entirely null — Excel format may have changed",
        )

    def test_lot_title_not_all_null(self):
        self.assertFalse(
            self.df["Lot Title"].isna().all(),
            "'Lot Title' column is entirely null",
        )

    def test_estimates_are_numeric(self):
        low = self.df["Low Estimate"].dropna()
        high = self.df["High Estimate"].dropna()
        if len(low) > 0:
            self.assertTrue(
                pd.to_numeric(low, errors="coerce").notna().any(),
                "'Low Estimate' values are not numeric",
            )
        if len(high) > 0:
            self.assertTrue(
                pd.to_numeric(high, errors="coerce").notna().any(),
                "'High Estimate' values are not numeric",
            )

    def test_size_column_has_values(self):
        sizes = self.df["Size"].dropna()
        self.assertGreater(len(sizes), 0, "'Size' column has no values")

    def test_qty_column_is_numeric(self):
        qty = self.df["Qty"].dropna()
        self.assertGreater(len(qty), 0, "'Qty' column has no values")
        self.assertTrue(
            pd.to_numeric(qty, errors="coerce").notna().any(),
            "'Qty' values are not numeric",
        )


if __name__ == "__main__":
    unittest.main()
