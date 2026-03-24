from __future__ import annotations

import re
import json
import unittest
from datetime import datetime

import demjson3
import requests

from tests.utils import live_html, live_json

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


if __name__ == "__main__":
    unittest.main()
