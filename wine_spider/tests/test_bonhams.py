from __future__ import annotations

import json
import unittest

import requests

from wine_spider.items import AuctionItem, LotDetailItem, LotItem
from wine_spider.services.bonhams_client import BonhamsClient

API_URL = "https://api01.bonhams.com/search-proxy/multi_search?use_cache=true&enable_lazy_filter=true"


class TestBonhamsAuctionAPI(unittest.TestCase):
    """Verify the Bonhams auction search API is accessible and parseable."""

    @classmethod
    def setUpClass(cls):
        cls.client = BonhamsClient()
        payload = cls.client.get_auction_search_payload()
        r = requests.post(
            API_URL,
            headers=cls.client.headers,
            json=payload,
            timeout=20,
        )
        r.raise_for_status()
        cls.json_data = r.json()
        cls.auctions = cls.client.parse_auction_api_response(cls.json_data)

    def test_api_returns_results(self):
        results = self.json_data.get("results", [])
        self.assertGreater(len(results), 0, "Auction API returned no results")
        hits = results[0].get("hits", [])
        self.assertGreater(len(hits), 0, "Auction API hits list is empty")

    def test_parse_yields_auction_items(self):
        self.assertGreater(len(self.auctions), 0)
        for a in self.auctions:
            self.assertIsInstance(a, AuctionItem)

    def test_auction_house_name(self):
        for a in self.auctions:
            self.assertEqual(a["auction_house"], "Bonhams")

    def test_auction_external_id_not_empty(self):
        for a in self.auctions:
            self.assertIsNotNone(a["external_id"])
            self.assertNotEqual(a["external_id"].strip(), "")

    def test_auction_has_dates(self):
        for a in self.auctions:
            self.assertIsNotNone(a["start_date"])

    def test_auction_year_is_valid(self):
        for a in self.auctions:
            self.assertIsNotNone(a["year"])
            self.assertGreaterEqual(a["year"], 2000)

    def test_auction_url_contains_bonhams(self):
        for a in self.auctions:
            self.assertIn("bonhams.com", a["url"])


class TestBonhamsLotsAPI(unittest.TestCase):
    """Verify the Bonhams lots API is accessible and parseable."""

    @classmethod
    def setUpClass(cls):
        cls.client = BonhamsClient()

        # Get a real auction_id first
        auction_payload = cls.client.get_auction_search_payload(per_page=5)
        r = requests.post(API_URL, headers=cls.client.headers, json=auction_payload, timeout=20)
        r.raise_for_status()
        auctions = cls.client.parse_auction_api_response(r.json())
        cls.auction_id = auctions[0]["external_id"]

        # Fetch lots for that auction
        lot_payload = cls.client.get_lot_search_payload(cls.auction_id, page=1, per_page=50)
        lots_r = requests.post(API_URL, headers=cls.client.headers, json=lot_payload, timeout=20)
        lots_r.raise_for_status()
        cls.lots_json = lots_r.json()
        cls.results = cls.client.parse_lot_api_response(cls.lots_json)

    def test_api_returns_hits(self):
        hits = self.lots_json.get("results", [{}])[0].get("hits", [])
        self.assertGreater(len(hits), 0, "Lots API returned no hits")

    def test_parse_yields_results(self):
        self.assertGreater(len(self.results), 0)

    def test_each_result_is_lot_and_details(self):
        for lot_item, lot_detail_items in self.results:
            self.assertIsInstance(lot_item, LotItem)
            self.assertIsInstance(lot_detail_items, list)

    def test_lot_name_not_empty(self):
        for lot_item, _ in self.results:
            self.assertIsNotNone(lot_item["lot_name"])
            self.assertNotEqual(lot_item["lot_name"].strip(), "")

    def test_lot_auction_id_matches(self):
        for lot_item, _ in self.results:
            self.assertEqual(lot_item["auction_id"], self.auction_id)

    def test_lot_currency_not_empty(self):
        for lot_item, _ in self.results:
            self.assertIsNotNone(lot_item["original_currency"])

    def test_lot_volume_is_numeric_or_none(self):
        for lot_item, _ in self.results:
            if lot_item["volume"] is not None:
                self.assertIsInstance(lot_item["volume"], (int, float))

    def test_lot_estimate_fields_are_numeric(self):
        for lot_item, _ in self.results:
            if lot_item["low_estimate"] is not None:
                self.assertIsInstance(lot_item["low_estimate"], (int, float))
            if lot_item["high_estimate"] is not None:
                self.assertIsInstance(lot_item["high_estimate"], (int, float))

    def test_lot_detail_vintage_in_range(self):
        for _, lot_detail_items in self.results:
            for detail in lot_detail_items:
                if detail["vintage"] is not None:
                    self.assertGreaterEqual(detail["vintage"], 1500)
                    self.assertLessEqual(detail["vintage"], 2100)


if __name__ == "__main__":
    unittest.main()
