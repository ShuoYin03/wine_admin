from __future__ import annotations

import re
import json
import unittest
from datetime import datetime
from unittest.mock import Mock

import demjson3
import requests
from scrapy.http import Request, TextResponse

from tests.utils import live_html, live_json
from wine_spider.helpers import build_lot_external_id
from wine_spider.items import LotDetailItem, LotItem
from wine_spider.services.christies_client import ChristiesClient
from wine_spider.spiders.christies import ChristiesSpider

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# November 2024 had a wine auction — reliable test month
CALENDAR_URL = "https://www.christies.com/en/results?year=2024&filters=|category_14|&month=11"


class TestChristiesCalendarPage(unittest.TestCase):
    """Verify the Christie's calendar page still embeds the expected JSON."""

    @classmethod
    def setUpClass(cls):
        cls.response = live_html(CALENDAR_URL, headers=HEADERS, timeout=20)
        match = re.search(
            r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n',
            cls.response.text,
            re.DOTALL,
        )
        cls.calendar_match = match
        cls.calendar_data = demjson3.decode(match.group(1)) if match else None

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_calendar_json_embedded(self):
        self.assertIsNotNone(
            self.calendar_match,
            "Pattern 'window.chrComponents.calendar' not found in page — Christie's may have changed their JS structure",
        )

    def test_calendar_has_events_key(self):
        if self.calendar_data is None:
            self.skipTest("Calendar JSON not found")
        events = self.calendar_data.get("data", {}).get("events", [])
        self.assertIsInstance(events, list, "'data.events' should be a list")

    def test_wine_events_have_required_fields(self):
        if self.calendar_data is None:
            self.skipTest("Calendar JSON not found")
        events = self.calendar_data.get("data", {}).get("events", [])
        wine_events = [e for e in events if "category_14" in e.get("filter_ids", "")]
        if not wine_events:
            self.skipTest("No wine events found in this month — try a different month")

        for event in wine_events[:3]:
            self.assertIn("title_txt", event, "Event missing 'title_txt'")
            self.assertIn("start_date", event, "Event missing 'start_date'")
            self.assertIn("landing_url", event, "Event missing 'landing_url'")

    def test_event_start_date_is_parseable(self):
        if self.calendar_data is None:
            self.skipTest("Calendar JSON not found")
        events = self.calendar_data.get("data", {}).get("events", [])
        wine_events = [e for e in events if "category_14" in e.get("filter_ids", "")]
        if not wine_events:
            self.skipTest("No wine events in this month")
        for event in wine_events[:3]:
            start = event.get("start_date")
            if start:
                parsed = datetime.fromisoformat(start)
                self.assertIsNotNone(parsed)


class TestChristiesAuctionPage(unittest.TestCase):
    """Verify a Christie's auction page still contains the expected lot filter JSON."""

    # Nov 2024 wine auction — uses window.chrComponents.lots (saved_lots type)
    AUCTION_URL = (
        "https://www.christies.com/en/auction/"
        "finest-and-rarest-wines-featuring-tignanello-s-50th-anniversary-collection"
        "-direct-from-the-estate-and-a-superb-european-collection-30286/"
    )

    @classmethod
    def setUpClass(cls):
        r = requests.get(cls.AUCTION_URL, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            raise unittest.SkipTest(f"Auction page returned {r.status_code}")
        cls.html = r.text

        pattern = r"window\.chrComponents\s*=\s*(\{.*?\});"
        match = re.search(pattern, cls.html, re.DOTALL)
        if not match:
            pattern = r"window\.chrComponents\.lots\s*=\s*(\{.*?\});"
            match = re.search(pattern, cls.html, re.DOTALL)
        cls.components_match = match
        if match:
            try:
                cls.components_data = json.loads(match.group(1))
            except Exception:
                cls.components_data = None
        else:
            cls.components_data = None

    def test_page_loads(self):
        self.assertGreater(len(self.html), 0)

    def test_chr_components_json_present(self):
        self.assertIsNotNone(
            self.components_match,
            "Neither 'window.chrComponents' nor 'window.chrComponents.lots' found — Christie's may have changed their JS structure",
        )

    def test_components_has_filters(self):
        if self.components_data is None:
            self.skipTest("chrComponents JSON not parseable")
        # Depending on the page type, filters are at different paths
        filters = (
            self.components_data.get("lots", {}).get("data", {}).get("filters", {}).get("groups", [])
            or self.components_data.get("data", {}).get("filters", {}).get("groups", [])
        )
        self.assertIsInstance(filters, list, "Filters groups should be a list")


class TestChristiesLotsAPI(unittest.TestCase):
    """Verify the Christie's lots search API is accessible and returns expected structure."""

    # Nov 2024 wine auction: sale_id=30286, sale_number=22688 (www.christies.com / saved_lots type)
    SALE_ID = 30286
    SALE_NUMBER = 22688

    @classmethod
    def setUpClass(cls):
        from wine_spider.services.christies_client import ChristiesClient
        cls.client = ChristiesClient()
        url = cls.client.saved_lots_query("paging", cls.SALE_ID, cls.SALE_NUMBER)
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code not in (200, 201):
            raise unittest.SkipTest(f"Lots API returned {r.status_code}")
        cls.json_data = r.json()

    def test_api_returns_data(self):
        self.assertIsInstance(self.json_data, dict, "Lots API should return a JSON object")

    def test_lots_key_present(self):
        self.assertIn("lots", self.json_data, f"'lots' key missing. Keys: {list(self.json_data.keys())}")

    def test_lots_list_not_empty(self):
        lots = self.json_data.get("lots", [])
        self.assertIsInstance(lots, list)
        self.assertGreater(len(lots), 0, "Lots list is empty")

    def test_lots_have_title(self):
        lots = self.json_data.get("lots", [])
        if not lots:
            self.skipTest("No lots returned")
        for lot in lots[:5]:
            self.assertIsInstance(lot, dict)
            title = lot.get("title_primary_txt")
            self.assertIsNotNone(title, f"Lot missing 'title_primary_txt'. Keys: {list(lot.keys())}")

    def test_lots_have_estimate(self):
        lots = self.json_data.get("lots", [])
        if not lots:
            self.skipTest("No lots returned")
        for lot in lots[:5]:
            self.assertIn("estimate_low", lot, f"Lot missing 'estimate_low'. Keys: {list(lot.keys())}")
            self.assertIn("estimate_high", lot, f"Lot missing 'estimate_high'")


class TestChristiesLotIds(unittest.TestCase):
    def test_common_lot_id_rule_combines_auction_and_source_lot_id(self):
        self.assertEqual(
            build_lot_external_id("31303#24697", "280563"),
            "31303#24697_280563",
        )

    def test_lot_and_detail_ids_are_namespaced_by_auction(self):
        spider = ChristiesSpider.__new__(ChristiesSpider)
        spider.lot_information_finder = Mock()
        spider.lot_information_finder.find_lot_information.return_value = (
            "Producer A",
            None,
            None,
            None,
        )

        request = Request(
            url="https://www.christies.com/api/lots",
            meta={
                "auction_id": "31303#24697",
                "sale_id": "4013",
                "sale_number": "24697",
                "all_filters": [],
                "saved": True,
            },
        )
        body = json.dumps(
            {
                "lots": [
                    {
                        "object_id": "280563",
                        "title_primary_txt": "Test Wine 2001",
                        "title_secondary_txt": "1 bottle",
                        "estimate_txt": "GBP 100 - 200",
                        "estimate_low": "100",
                        "estimate_high": "200",
                        "price_realised": None,
                        "end_date": "2025-12-06T00:00:00",
                    }
                ]
            }
        ).encode("utf-8")
        response = TextResponse(
            url=request.url,
            request=request,
            body=body,
            encoding="utf-8",
        )

        results = list(spider.parse_initial_request(response))
        lot = next(item for item in results if isinstance(item, LotItem))
        detail = next(item for item in results if isinstance(item, LotDetailItem))

        self.assertEqual(lot["external_id"], "31303#24697_280563")
        self.assertEqual(detail["lot_id"], "31303#24697_280563")
        self.assertEqual(lot["auction_id"], "31303#24697")


class TestChristiesFilterFlow(unittest.TestCase):
    def make_spider(self):
        spider = ChristiesSpider.__new__(ChristiesSpider)
        spider.client = ChristiesClient()
        spider.lot_information_finder = Mock()
        spider.lot_information_finder.find_lot_information.return_value = (
            "Producer A",
            None,
            None,
            None,
        )
        return spider

    def make_lots(self):
        lot = LotItem()
        lot["external_id"] = "23300#5603_5356888"
        lot["auction_id"] = "23300#5603"
        lot["lot_name"] = "Petrus 1982"
        return {
            "5356888": {
                "lot_item": lot,
                "lot_detail_info": {
                    "lot_producer": [],
                    "vintage": ["1982"],
                    "unit_format": [],
                    "wine_colour": [],
                },
            }
        }

    def make_filter_response(self, status, all_filters, retry_count=0, body=None):
        request = Request(
            url="https://www.christies.com/api/discoverywebsite/auctionpages/lotsearch",
            meta={
                "auction_id": "23300#5603",
                "sale_id": 23300,
                "sale_number": 5603,
                "all_filters": all_filters,
                "saved": True,
                "lots": self.make_lots(),
                "current_filter": "CoaArtists{Vega-Sicilia%2c%22Unico%22}",
                "filter_retry_count": retry_count,
            },
        )
        if body is None:
            body = b"" if status >= 400 else b'{"lots":[]}'
        return TextResponse(
            url=request.url,
            request=request,
            status=status,
            body=body,
            encoding="utf-8",
        )

    def test_filter_request_allows_400_response_to_reach_callback(self):
        spider = self.make_spider()

        request = next(
            spider.yield_request(
                saved=True,
                auction_id="23300#5603",
                sale_id=23300,
                sale_number=5603,
                all_filters=[],
                current_filter="CoaArtists{Vega-Sicilia%2c%22Unico%22}",
                lots=self.make_lots(),
                callback=spider.parse_filters,
            )
        )

        self.assertEqual(request.meta["handle_httpstatus_list"], [400])

    def test_parse_filters_retries_400_filter_before_continuing(self):
        spider = self.make_spider()
        response = self.make_filter_response(
            status=400,
            all_filters=["Producer{Yquem}"],
        )

        results = list(spider.parse_filters(response))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertEqual(results[0].meta["current_filter"], "CoaArtists{Vega-Sicilia%2c%22Unico%22}")
        self.assertEqual(results[0].meta["filter_retry_count"], 1)
        self.assertEqual(results[0].meta["all_filters"], ["Producer{Yquem}"])

    def test_parse_filters_retries_malformed_filter_response(self):
        spider = self.make_spider()
        response = self.make_filter_response(
            status=200,
            all_filters=["Producer{Yquem}"],
            body=b"",
        )

        results = list(spider.parse_filters(response))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertEqual(results[0].meta["current_filter"], "CoaArtists{Vega-Sicilia%2c%22Unico%22}")
        self.assertEqual(results[0].meta["filter_retry_count"], 1)

    def test_parse_filters_continues_after_400_filter_retries_are_exhausted(self):
        spider = self.make_spider()
        response = self.make_filter_response(
            status=400,
            all_filters=["Producer{Yquem}"],
            retry_count=2,
        )

        results = list(spider.parse_filters(response))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertIn("filterids=%7CProducer%7BYquem%7D%7C", results[0].url)
        self.assertEqual(results[0].meta["filter_retry_count"], 0)

    def test_parse_filters_yields_lots_after_last_400_filter_response(self):
        spider = self.make_spider()
        response = self.make_filter_response(status=400, all_filters=[], retry_count=2)

        results = list(spider.parse_filters(response))

        self.assertTrue(any(isinstance(item, LotItem) for item in results))
        self.assertTrue(any(isinstance(item, LotDetailItem) for item in results))


if __name__ == "__main__":
    unittest.main()
