from __future__ import annotations

import json
import unittest

import requests
from scrapy.http import HtmlResponse, TextResponse

from wine_spider.services import SothebysClient

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
GRAPHQL_HEADERS = {
    **HEADERS,
    "Content-Type": "application/json",
}

RESULTS_URL = (
    "https://www.sothebys.com/en/results"
    "?from=&to="
    "&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000"
    "&f2=00000164-609a-d1db-a5e6-e9fffcc80000"
    "&q="
)


class TestSothebysResultsPage(unittest.TestCase):
    """Verify the Sotheby's results listing page still embeds sale-price UUIDs."""

    @classmethod
    def setUpClass(cls):
        r = requests.get(RESULTS_URL, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            raise unittest.SkipTest(f"Results page returned {r.status_code}")
        cls.response = HtmlResponse(url=RESULTS_URL, body=r.content)

        uuids = cls.response.css(
            ".Card-salePrice span::attr(data-dynamic-sale-price-uuid)"
        ).getall()
        cls.uuids = uuids

        if uuids:
            asset_url = (
                f"https://www.sothebys.com/data/api/asset.actions.json"
                f"?id={','.join(uuids[:5])}"
            )
            asset_r = requests.get(asset_url, headers=HEADERS, timeout=20)
            cls.asset_data = asset_r.json() if asset_r.status_code == 200 else {}
        else:
            cls.asset_data = {}

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_uuid_spans_found(self):
        self.assertGreater(
            len(self.uuids), 0,
            "No 'data-dynamic-sale-price-uuid' spans found — "
            "Sotheby's results page structure may have changed",
        )

    def test_asset_api_returns_viking_ids(self):
        if not self.uuids:
            self.skipTest("No UUIDs found on listing page")
        self.assertGreater(
            len(self.asset_data), 0,
            "Asset API returned no data",
        )
        for uuid, asset in list(self.asset_data.items())[:3]:
            self.assertIn(
                "vikingId", asset,
                f"Asset entry for {uuid} missing 'vikingId'. Keys: {list(asset.keys())}",
            )
            self.assertIsNotNone(asset.get("vikingId"))

    def test_asset_api_returns_urls(self):
        if not self.asset_data:
            self.skipTest("Asset API data not available")
        for _, asset in list(self.asset_data.items())[:3]:
            url = asset.get("url", "")
            self.assertIn("sothebys.com", url, f"Unexpected asset URL: {url}")


class TestSothebysAuctionGraphQL(unittest.TestCase):
    """Verify the Sotheby's GraphQL auction API is accessible and returns expected structure."""

    @classmethod
    def setUpClass(cls):
        cls.client = SothebysClient()

        # Dynamically get a viking_id from the live listing
        r = requests.get(RESULTS_URL, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            raise unittest.SkipTest(f"Results page returned {r.status_code}")

        listing = HtmlResponse(url=RESULTS_URL, body=r.content)
        uuids = listing.css(
            ".Card-salePrice span::attr(data-dynamic-sale-price-uuid)"
        ).getall()
        if not uuids:
            raise unittest.SkipTest("No UUIDs found on listing page")

        asset_url = (
            f"https://www.sothebys.com/data/api/asset.actions.json"
            f"?id={','.join(uuids[:5])}"
        )
        asset_r = requests.get(asset_url, headers=HEADERS, timeout=20)
        if asset_r.status_code != 200:
            raise unittest.SkipTest(f"Asset API returned {asset_r.status_code}")

        asset_data = asset_r.json()
        # Find a wine-related auction
        viking_id = None
        for _, asset in asset_data.items():
            url = asset.get("url", "")
            if "wine" in url or "spirits" in url or "cellar" in url or "whisky" in url:
                viking_id = asset.get("vikingId")
                break
        if viking_id is None:
            # Just use the first available
            first_asset = next(iter(asset_data.values()), {})
            viking_id = first_asset.get("vikingId")

        if not viking_id:
            raise unittest.SkipTest("Could not find a viking_id from listing")

        cls.viking_id = viking_id
        payload = cls.client.auction_query(viking_id)
        gr = requests.post(
            cls.client.api_url,
            headers=GRAPHQL_HEADERS,
            json=payload,
            timeout=20,
        )
        if gr.status_code != 200:
            raise unittest.SkipTest(f"GraphQL API returned {gr.status_code}")
        cls.gql_data = gr.json()

    def test_graphql_returns_data(self):
        self.assertIsInstance(self.gql_data, dict)
        self.assertIn(
            "data", self.gql_data,
            f"GraphQL response missing 'data' key. Keys: {list(self.gql_data.keys())}",
        )

    def test_auction_object_present(self):
        auction = self.gql_data.get("data", {}).get("auction")
        self.assertIsNotNone(
            auction,
            "GraphQL response 'data.auction' is None — auction may not exist or query changed",
        )

    def test_auction_has_id(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        self.assertIn("auctionId", auction, "Auction missing 'auctionId'")
        self.assertEqual(auction["auctionId"], self.viking_id)

    def test_auction_has_title(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        title = auction.get("title")
        self.assertIsNotNone(title, "Auction missing 'title'")
        self.assertNotEqual(title.strip(), "")

    def test_auction_has_currency(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        self.assertIn("currency", auction, "Auction missing 'currency'")
        self.assertIsNotNone(auction.get("currency"))

    def test_auction_has_location(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        location = auction.get("location")
        self.assertIsNotNone(location, "Auction missing 'location'")
        self.assertIn("name", location, "Location missing 'name'")

    def test_auction_has_dates(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        dates = auction.get("dates")
        self.assertIsNotNone(dates, "Auction missing 'dates'")
        self.assertIn("closed", dates, "Dates missing 'closed' field")

    def test_auction_state_is_string(self):
        auction = self.gql_data.get("data", {}).get("auction", {})
        if auction is None:
            self.skipTest("auction data is None")
        state = auction.get("state")
        self.assertIsNotNone(state, "Auction missing 'state'")
        self.assertIsInstance(state, str)


class TestSothebysAlgoliaAPIStructure(unittest.TestCase):
    """Verify the SothebysClient.algolia_api() generates a valid request structure.

    NOTE: The Algolia API requires a per-session API key extracted from the
    Playwright-rendered auction page. This test class only validates the URL and
    payload structure — it does NOT make a live Algolia request.
    """

    def setUp(self):
        self.client = SothebysClient()
        self.viking_id = "f882c55f-c300-407d-852e-42ba3963cb98"  # known past auction
        self.dummy_key = "dummy_algolia_key"

    def test_algolia_api_returns_url_headers_payload(self):
        url, headers, payload = self.client.algolia_api(self.viking_id, self.dummy_key, 0)
        self.assertIsInstance(url, str)
        self.assertIsInstance(headers, dict)
        self.assertIsInstance(payload, dict)

    def test_algolia_url_contains_algolia_net(self):
        url, _, _ = self.client.algolia_api(self.viking_id, self.dummy_key, 0)
        self.assertIn("algolia.net", url)

    def test_algolia_headers_include_api_key(self):
        _, headers, _ = self.client.algolia_api(self.viking_id, self.dummy_key, 0)
        self.assertIn("x-algolia-api-key", headers)
        self.assertEqual(headers["x-algolia-api-key"], self.dummy_key)

    def test_algolia_payload_filters_by_auction(self):
        _, _, payload = self.client.algolia_api(self.viking_id, self.dummy_key, 0)
        filters = payload.get("filters", "")
        self.assertIn(self.viking_id, filters, "Algolia filter doesn't include viking_id")

    def test_algolia_payload_has_pagination(self):
        _, _, payload0 = self.client.algolia_api(self.viking_id, self.dummy_key, 0)
        _, _, payload1 = self.client.algolia_api(self.viking_id, self.dummy_key, 1)
        self.assertEqual(payload0.get("page"), 0)
        self.assertEqual(payload1.get("page"), 1)


if __name__ == "__main__":
    unittest.main()
