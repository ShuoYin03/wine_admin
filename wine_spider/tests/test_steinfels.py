from __future__ import annotations

import unittest

import requests

from tests.utils import live_json, make_json_response
from wine_spider.items import AuctionItem, LotDetailItem, LotItem
from wine_spider.helpers.steinfels.description_parser import parse_description
from wine_spider.services.steinfels_client import SteinfelsClient

AUCTION_API_URL = "https://auktionen.steinfelsweine.ch/api/auctions?archived=true"
HEADERS = {"x-api-version": "1.15"}


class RecordingLotInformationFinder:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def find_lot_information(self, title):
        self.calls.append(title)
        return self.result


def make_lots_response(*lots):
    return {
        "@related": {
            "auctions": [
                {
                    "id": 150,
                    "currency": "CHF",
                }
            ],
            "parts": [],
        },
        "items": list(lots),
    }


def make_wine_catalog_lots_response(*lots):
    response = make_lots_response(*lots)
    response["@related"]["parts"] = [
        {
            "id": 95,
            "description": "Weine",
        }
    ]
    return response


def make_lot(lot_id, description):
    return {
        "id": lot_id,
        "description": description,
        "startingBid": 280,
        "hammerPrice": 350,
        "basePrice": 350,
        "upperBasePrice": 550,
        "state": "sold",
    }


class TestSteinfelsLotTypeClassification(unittest.TestCase):
    def test_whisky_lot_does_not_use_wine_metadata_match(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("El Enemigo", "Mendoza", "Mendoza", "Argentina")
        )
        response = make_lots_response(
            make_lot(
                19179,
                """
                <strong>WHISKY Speyside Single Malt</strong><BR>
                Inchgower 22years old, Rare Malts Selection 1974<BR>
                d 1974, b 09.1997, 55.7%, no 0560<BR>
                <strong>1 Flasche</strong><BR>
                """,
            )
        )

        results = client.parse_lot_api_response(response, auction_catalog_id="150", url="test")

        lot_item, lot_detail_items = results[0]
        self.assertEqual(lot_item["lot_type"], ["Spirits"])
        self.assertEqual(client.lot_information_finder.calls, [])
        self.assertIsNone(lot_item.get("region"))
        self.assertIsNone(lot_item.get("sub_region"))
        self.assertIsNone(lot_item.get("country"))
        self.assertNotEqual(lot_detail_items[0]["lot_producer"], "El Enemigo")

    def test_wine_lot_still_uses_wine_metadata_match(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("Chateau Latour", "Bordeaux", "Pauillac", "France")
        )
        response = make_lots_response(
            make_lot(
                2,
                """
                <strong>Chateau Latour</strong><BR>
                Pauillac 1982<BR>
                1 Flasche 75 cl<BR>
                """,
            )
        )

        results = client.parse_lot_api_response(response, auction_catalog_id="150", url="test")

        lot_item, lot_detail_items = results[0]
        self.assertEqual(lot_item["lot_type"], ["Wine"])
        self.assertEqual(client.lot_information_finder.calls, ["Chateau Latour"])
        self.assertEqual(lot_item["region"], "Bordeaux")
        self.assertEqual(lot_item["sub_region"], "Pauillac")
        self.assertEqual(lot_item["country"], "France")
        self.assertEqual(lot_detail_items[0]["lot_producer"], "Chateau Latour")

    def test_wine_catalog_context_keeps_non_spirit_lot_on_wine_path(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("Fouquerand", "Burgundy", "Hautes Cotes de Beaune", "France")
        )
        response = make_wine_catalog_lots_response(
            make_lot(
                4,
                """
                <strong>FOUQUERAND</strong><BR>
                Hautes Côtes de Beaune blanc 2003<BR>
                6 Flaschen OC<BR>
                """,
            )
        )

        results = client.parse_lot_api_response(response, auction_catalog_id="90", url="test")

        lot_item, lot_detail_items = results[0]
        self.assertEqual(lot_item["lot_type"], ["Wine"])
        self.assertEqual(client.lot_information_finder.calls, ["FOUQUERAND"])
        self.assertEqual(lot_item["region"], "Burgundy")
        self.assertEqual(lot_item["sub_region"], "Hautes Cotes de Beaune")
        self.assertEqual(lot_item["country"], "France")
        self.assertEqual(lot_detail_items[0]["lot_producer"], "Fouquerand")

    def test_sub_item_region_country_counters_are_independent(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("Domaine Example", "Burgundy", "Cote de Nuits", "France")
        )
        response = make_wine_catalog_lots_response(
            make_lot(
                10,
                """
                <strong>Mixed Burgundy case</strong><BR>
                1x Domaine Example 2010<BR>
                1x Domaine Example 2011<BR>
                """,
            )
        )

        results = client.parse_lot_api_response(response, auction_catalog_id="90", url="test")

        lot_item, _ = results[0]
        self.assertEqual(lot_item["region"], "Burgundy")
        self.assertEqual(lot_item["sub_region"], "Cote de Nuits")
        self.assertEqual(lot_item["country"], "France")

    def test_null_upper_estimate_uses_description_high_estimate(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("Chateau Angelus", "Bordeaux", "Saint-Emilion", "France")
        )
        lot = make_lot(
            13832,
            """
            <strong>Chateau Angelus</strong><BR>
            1er Cru B Saint-Emilion 1982<BR>
            1 Flasche 75 cl<BR>
            <br/><div>Estimate price: <span>160 - 240 CHF</span></div>
            """,
        )
        lot["basePrice"] = 160
        lot["upperBasePrice"] = None
        response = make_wine_catalog_lots_response(lot)

        results = client.parse_lot_api_response(response, auction_catalog_id="90", url="test")

        lot_item, _ = results[0]
        self.assertEqual(lot_item["low_estimate"], 160)
        self.assertEqual(lot_item["high_estimate"], 240)

    def test_b_tag_title_is_parsed_and_condition_notes_do_not_become_volume(self):
        result = parse_description(
            """
            <b>RIBERA DEL DUERO Bodegas Alion (Vega Sicilia),</b><br>
            Alion, 1995<br>
            2in, 1bn, 1ts, glv<br>
            <b>4 Flaschen</b><br>
            """
        )

        self.assertEqual(result["title"], "RIBERA DEL DUERO Bodegas Alion (Vega Sicilia)")
        self.assertEqual(result["producer"], "Alion")
        self.assertEqual(result["quantity"], 4)
        self.assertEqual(result["unit_format"], "flaschen")
        self.assertEqual(result["total_volume_ml"], 3000)

    def test_accented_producer_name_does_not_match_centilitre_unit(self):
        result = parse_description(
            """
            <strong>Bordeaux</strong><br>
            Cru Bourgeois Haut-Médoc mixed, 2015<br>
            6x Cambon La Pelouse<br>
            6x Clément-Pichon<br>
            <b>12 Flaschen 6er OHK</b><br>
            Estimate price: 100 - 120 CHF<br>
            """
        )

        self.assertEqual(result["title"], "Bordeaux")
        self.assertEqual(result["quantity"], 12)
        self.assertEqual(result["unit_format"], "flaschen 6er ohk")
        self.assertEqual(result["total_volume_ml"], 9000)

    def test_german_doppelmagnum_unit_is_parsed(self):
        result = parse_description(
            """
            <strong>Château Haut-Brion</strong><br>
            1er Cru Pessac-Léognan, 2000<br>
            in, lv<br>
            <b>1 Doppelmagnum</b><br>
            """
        )

        self.assertEqual(result["quantity"], 1)
        self.assertEqual(result["unit_format"], "doppelmagnum")
        self.assertEqual(result["total_volume_ml"], 3000)

    def test_collection_box_uses_sub_item_quantities_as_bottles(self):
        result = parse_description(
            """
            <strong>TEMENT</strong><br>
            Parzellenkollektion Zieregg Sauvignon Blanc, 2019<br>
            Parzellenkollektion mit 6 Flaschen:<br>
            2x Karmeliten Berg Brunnenhaus<br>
            2x Oberer Steilriegel<br>
            2x Weisse Wand Rückenstück<br>
            <b>1 Sammlerbox OHK</b><br>
            """
        )

        self.assertEqual(result["quantity"], 6)
        self.assertEqual(result["unit_format"], "flaschen")
        self.assertEqual(result["total_volume_ml"], 4500)

    def test_b_tag_title_is_used_for_wine_metadata_lookup(self):
        client = SteinfelsClient()
        client.lot_information_finder = RecordingLotInformationFinder(
            ("Alion", "Ribera del Duero", "Ribera del Duero", "Spain")
        )
        response = make_wine_catalog_lots_response(
            make_lot(
                72507,
                """
                <b>RIBERA DEL DUERO Bodegas Alion (Vega Sicilia),</b><br>
                Alion, 1995<br>
                2in, 1bn, 1ts, glv<br>
                <b>4 Flaschen</b><br>
                """,
            )
        )

        results = client.parse_lot_api_response(response, auction_catalog_id="480", url="test")

        lot_item, lot_detail_items = results[0]
        self.assertEqual(
            lot_item["lot_name"],
            "RIBERA DEL DUERO Bodegas Alion (Vega Sicilia)",
        )
        self.assertEqual(
            client.lot_information_finder.calls,
            ["RIBERA DEL DUERO Bodegas Alion (Vega Sicilia)"],
        )
        self.assertEqual(lot_item["volume"], 3000)
        self.assertEqual(lot_item["unit"], 4)
        self.assertEqual(lot_item["region"], "Ribera del Duero")
        self.assertEqual(lot_item["country"], "Spain")
        self.assertEqual(lot_detail_items[0]["lot_producer"], "Alion")


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
