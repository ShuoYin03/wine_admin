from __future__ import annotations

import json
import unittest
import asyncio

import pandas as pd
from curl_cffi import requests as cffi_requests
from scrapy import Request
from scrapy.http import HtmlResponse
from scrapy.http import TextResponse

from wine_spider.helpers import (
    AUCTION_LANDING_URL,
    build_zachys_categories_url,
    extract_zachys_lot_count_from_categories,
    extract_zachys_past_catalog_links,
    parse_volume,
)
from wine_spider.items import LotItem
from wine_spider.spiders.zachys import ZachysSpider


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/142.0.0.0 Safari/537.36"
    )
}

XHR_HEADERS = {
    **HEADERS,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def cffi_get(url: str, timeout: int = 30, headers: dict | None = None):
    return cffi_requests.get(
        url,
        impersonate="chrome142",
        timeout=timeout,
        headers=headers or HEADERS,
    )


def fetch_html(url: str, timeout: int = 30) -> HtmlResponse:
    response = cffi_get(url, timeout=timeout)
    response.raise_for_status()
    return HtmlResponse(url=url, body=response.content, encoding="utf-8")


async def collect_async_items(async_iterable):
    return [item async for item in async_iterable]


def test_parse_volume_accepts_zachys_ounces_size():
    assert parse_volume("16 oz") == 454.4


def test_zachys_excel_parser_creates_lot_when_html_lot_is_missing(monkeypatch):
    spider = ZachysSpider()
    spider.lot_information_finder = object()

    monkeypatch.setattr(
        "wine_spider.spiders.zachys.pd.read_excel",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {
                    "Lot": 1.0,
                    "Lot Title": "Test Wine 2020",
                    "Size": "16 oz",
                    "Lot Details": "",
                    "Qty": 1,
                    "Low Estimate": 100,
                    "High Estimate": 200,
                    "Region": "California",
                    "Country": None,
                    "Producer": "Test Producer",
                    "Vintage": "2020",
                    "Class": "Red",
                    "URL": "Lot 1",
                }
            ]
        ),
    )
    request = Request(
        "https://bid.zachys.com/downloads/auction/167/test.xls",
        meta={"auction_id": "zachys_167", "lots": {}},
    )
    response = TextResponse(request.url, body=b"", request=request)

    items = asyncio.run(collect_async_items(spider.parse_excel(response)))
    lot_items = [item for item in items if isinstance(item, LotItem)]

    assert len(lot_items) == 1
    assert lot_items[0]["external_id"] == "zachys_167_1"
    assert lot_items[0]["volume"] == 454.4
    assert lot_items[0]["success"] is True


def test_zachys_excel_parser_skips_html_only_lots(monkeypatch):
    spider = ZachysSpider()
    spider.lot_information_finder = object()

    monkeypatch.setattr(
        "wine_spider.spiders.zachys.pd.read_excel",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {
                    "Lot": 1,
                    "Lot Title": "Test Wine 2020",
                    "Size": "750ml",
                    "Lot Details": "",
                    "Qty": 1,
                    "Low Estimate": 100,
                    "High Estimate": 200,
                    "Region": "California",
                    "Country": None,
                    "Producer": "Test Producer",
                    "Vintage": "2020",
                    "Class": "Red",
                    "URL": "Lot 1",
                }
            ]
        ),
    )
    html_only = ZachysSpider.build_empty_lot_record()
    html_only_lot = LotItem()
    html_only_lot["auction_id"] = "zachys_117"
    html_only_lot["external_id"] = "zachys_117_1575"
    html_only_lot["success"] = False
    html_only["lot_item"] = html_only_lot
    request = Request(
        "https://bid.zachys.com/downloads/auction/117/test.xls",
        meta={
            "auction_id": "zachys_117",
            "lots": {"1575": html_only},
        },
    )
    response = TextResponse(request.url, body=b"", request=request)

    items = asyncio.run(collect_async_items(spider.parse_excel(response)))
    lot_items = [item for item in items if isinstance(item, LotItem)]

    assert [item["external_id"] for item in lot_items] == ["zachys_117_1"]


def test_zachys_excel_parser_respects_expected_lot_count(monkeypatch):
    spider = ZachysSpider()
    spider.lot_information_finder = object()

    monkeypatch.setattr(
        "wine_spider.spiders.zachys.pd.read_excel",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {
                    "Lot": 1,
                    "Lot Title": "Expected Wine",
                    "Size": "750ml",
                    "Lot Details": "",
                    "Qty": 1,
                    "Low Estimate": 100,
                    "High Estimate": 200,
                    "Region": "California",
                    "Country": None,
                    "Producer": "Expected Producer",
                    "Vintage": "2020",
                    "Class": "Red",
                    "URL": "Lot 1",
                },
                {
                    "Lot": 2,
                    "Lot Title": "Extra Wine",
                    "Size": "750ml",
                    "Lot Details": "",
                    "Qty": 1,
                    "Low Estimate": 100,
                    "High Estimate": 200,
                    "Region": "California",
                    "Country": None,
                    "Producer": "Extra Producer",
                    "Vintage": "2020",
                    "Class": "Red",
                    "URL": "Lot 2",
                },
            ]
        ),
    )
    request = Request(
        "https://bid.zachys.com/downloads/auction/152/test.xls",
        meta={
            "auction_id": "zachys_152",
            "lots": {},
            "expected_lot_count": 1,
        },
    )
    response = TextResponse(request.url, body=b"", request=request)

    items = asyncio.run(collect_async_items(spider.parse_excel(response)))
    lot_items = [item for item in items if isinstance(item, LotItem)]

    assert [item["external_id"] for item in lot_items] == ["zachys_152_1"]


class TestZachysAuctionLandingPage(unittest.TestCase):
    """Verify the current Zachys auction landing page exposes past catalog links."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.response = fetch_html(AUCTION_LANDING_URL)
        except Exception as exc:
            raise unittest.SkipTest(f"Zachys auction landing page unreachable: {exc}")

        cls.catalog_links = extract_zachys_past_catalog_links(cls.response.text)

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_past_catalog_links_are_discoverable(self):
        self.assertGreater(len(self.catalog_links), 0)
        first = self.catalog_links[0]
        self.assertTrue(first.auction_id.isdigit())
        self.assertIn("bid.zachys.com/auctions/catalog/id/", first.catalog_url)
        self.assertTrue(first.title)

    def test_past_catalog_links_are_deduplicated(self):
        auction_ids = [link.auction_id for link in self.catalog_links]
        self.assertEqual(len(auction_ids), len(set(auction_ids)))


class TestZachysCategoryEndpoint(unittest.TestCase):
    """Verify Zachys lot counts can be read from the current catalog XHR endpoint."""

    @classmethod
    def setUpClass(cls):
        try:
            landing = fetch_html(AUCTION_LANDING_URL)
        except Exception as exc:
            raise unittest.SkipTest(f"Zachys auction landing page unreachable: {exc}")

        links = extract_zachys_past_catalog_links(landing.text)
        if not links:
            raise unittest.SkipTest("No Zachys past catalog links found")

        cls.catalog = links[0]
        headers = {**XHR_HEADERS, "Referer": cls.catalog.catalog_url}
        try:
            response = cffi_get(
                build_zachys_categories_url(cls.catalog.auction_id),
                timeout=30,
                headers=headers,
            )
            response.raise_for_status()
        except Exception as exc:
            raise unittest.SkipTest(f"Zachys category endpoint unreachable: {exc}")

        try:
            cls.payload = json.loads(response.text)
        except Exception as exc:
            raise unittest.SkipTest(f"Zachys category endpoint returned invalid JSON: {exc}")

    def test_category_endpoint_returns_success(self):
        self.assertTrue(self.payload.get("success"))

    def test_category_endpoint_has_lot_count(self):
        self.assertGreater(extract_zachys_lot_count_from_categories(self.payload), 0)

    def test_category_endpoint_has_expected_category_shape(self):
        categories = (self.payload.get("payload") or {}).get("categories") or []
        self.assertGreater(len(categories), 0)
        for field in ("id", "name", "lots_qty"):
            self.assertIn(field, categories[0])


if __name__ == "__main__":
    unittest.main()
