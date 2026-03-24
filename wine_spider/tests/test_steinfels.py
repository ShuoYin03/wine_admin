from __future__ import annotations

import unittest

import requests

from tests.utils import live_json, make_json_response
from wine_spider.items import AuctionItem, LotDetailItem, LotItem
from wine_spider.services.steinfels_client import SteinfelsClient

AUCTION_API_URL = "https://auktionen.steinfelsweine.ch/api/auctions?archived=true"
HEADERS = {"x-api-version": "1.15"}


class TestSteinfelsAuctionAPI(unittest.TestCase):
    """Verify the Steinfels auction list API is accessible and parseable."""

    @classmethod
    def setUpClass(cls):
        cls.client = SteinfelsClient()
        r = requests.get(AUCTION_API_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        cls.raw = r.content
        cls.json_data = r.json()
        cls.auctions, cls.catalog_ids = cls.client.parse_auction_api_response(cls.json_data)

    def test_api_returns_data(self):
        self.assertIsInstance(self.json_data, list)
        self.assertGreater(len(self.json_data), 0, "Auction API returned empty list")

    def test_parse_yields_auction_items(self):
        self.assertGreater(len(self.auctions), 0)
        for a in self.auctions:
            self.assertIsInstance(a, AuctionItem)

    def test_auction_external_id_format(self):
        for a in self.auctions:
            self.assertTrue(
                a["external_id"].startswith("steinfels_"),
                f"external_id should start with 'steinfels_', got: {a['external_id']}",
            )

    def test_auction_house_name(self):
        for a in self.auctions:
            self.assertEqual(a["auction_house"], "Steinfels")

    def test_auction_has_dates(self):
        for a in self.auctions:
            self.assertIsNotNone(a["start_date"], "start_date should not be None")

    def test_auction_url_is_valid(self):
        for a in self.auctions:
            self.assertIn("steinfelsweine.ch", a["url"])

    def test_catalog_ids_match_auctions(self):
        self.assertEqual(len(self.auctions), len(self.catalog_ids))


class TestSteinfelsLotsAPI(unittest.TestCase):
    """Verify the Steinfels lots API is accessible and parseable."""

    @classmethod
    def setUpClass(cls):
        cls.client = SteinfelsClient()

        # Fetch the first available catalog_id from the auction API
        r = requests.get(AUCTION_API_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        auctions, catalog_ids = cls.client.parse_auction_api_response(r.json())

        # Use the most recent past auction's catalog_id
        cls.catalog_id = catalog_ids[0]
        cls.auction_url = cls.client.get_lot_api_url(cls.catalog_id, page=1)

        lots_r = requests.get(cls.auction_url, headers=HEADERS, timeout=15)
        lots_r.raise_for_status()
        cls.raw = lots_r.content
        cls.lots_json = lots_r.json()

        cls.results = cls.client.parse_lot_api_response(
            response=cls.lots_json,
            auction_catalog_id=cls.catalog_id,
            url=cls.auction_url,
        )

    def test_api_returns_items(self):
        self.assertIn("items", self.lots_json, "Lots API response missing 'items' key")

    def test_parse_yields_results(self):
        self.assertGreater(len(self.results), 0, "parse_lot_api_response returned no lots")

    def test_each_result_is_lot_and_details(self):
        for lot_item, lot_detail_items in self.results:
            self.assertIsInstance(lot_item, LotItem)
            self.assertIsInstance(lot_detail_items, list)
            self.assertGreater(len(lot_detail_items), 0)
            for detail in lot_detail_items:
                self.assertIsInstance(detail, LotDetailItem)

    def test_lot_external_id_format(self):
        for lot_item, _ in self.results:
            self.assertTrue(
                lot_item["external_id"].startswith("steinfels_"),
                f"lot external_id malformed: {lot_item['external_id']}",
            )

    def test_lot_name_not_empty(self):
        for lot_item, _ in self.results:
            self.assertIsNotNone(lot_item["lot_name"])
            self.assertNotEqual(lot_item["lot_name"].strip(), "")

    def test_lot_currency_not_empty(self):
        for lot_item, _ in self.results:
            self.assertIsNotNone(lot_item["original_currency"])

    def test_lot_volume_is_numeric_or_none(self):
        for lot_item, _ in self.results:
            if lot_item["volume"] is not None:
                self.assertIsInstance(lot_item["volume"], (int, float))

    def test_lot_detail_has_producer(self):
        for _, lot_detail_items in self.results:
            for detail in lot_detail_items:
                self.assertIsNotNone(
                    detail["lot_producer"], "lot_producer should not be None"
                )

    def test_lot_detail_vintage_in_range(self):
        for _, lot_detail_items in self.results:
            for detail in lot_detail_items:
                if detail["vintage"] is not None:
                    self.assertGreaterEqual(detail["vintage"], 1500)
                    self.assertLessEqual(detail["vintage"], 2100)


if __name__ == "__main__":
    unittest.main()
