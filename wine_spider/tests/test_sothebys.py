from __future__ import annotations

import json
import unittest

import requests
from scrapy.http import HtmlResponse, Request, TextResponse

from wine_spider.items import CombinedLotItem, LotDetailItem, LotItem
from wine_spider.services import SothebysClient
from wine_spider.spiders import sothebys as sothebys_module
from wine_spider.spiders.sothebys import SothebysSpider

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

    def test_algolia_search_key_query_filters_by_auction(self):
        payload = self.client.algolia_search_key_query(self.viking_id)

        self.assertEqual(payload["operationName"], "AlgoliaSearchKeyQuery")
        self.assertIn("algoliaSearchKey", payload["query"])
        self.assertEqual(
            payload["variables"]["filters"],
            [{"key": "auctionId", "value": self.viking_id}],
        )

    def test_extract_algolia_api_key_returns_none_when_page_uses_graphql_key(self):
        html = """
        <html>
          <script id="__NEXT_DATA__" type="application/json">
            {"props":{"pageProps":{"auctionId":"auction-1"}}}
          </script>
        </html>
        """

        self.assertIsNone(self.client.extract_algolia_api_key(html))


class TestSothebysAlgoliaFlow(unittest.TestCase):
    def setUp(self):
        self.spider = SothebysSpider.__new__(SothebysSpider)
        self.spider.client = SothebysClient()
        self.spider.base_url = "https://www.sothebys.com"

    def make_json_response(self, payload, meta=None):
        request = Request(
            url="https://clientapi.prod.sothelabs.com/graphql",
            meta=meta or {},
        )
        return TextResponse(
            url=request.url,
            request=request,
            body=json.dumps(payload).encode("utf-8"),
            encoding="utf-8",
        )

    def test_parse_algolia_key_response_creates_first_lot_request(self):
        response = self.make_json_response(
            {"data": {"algoliaSearchKey": {"key": "real-key"}}},
            meta={"viking_id": "auction-1", "token": None},
        )

        results = list(self.spider.parse_algolia_key_response(response))

        self.assertEqual(len(results), 1)
        request = results[0]
        self.assertIn("algolia.net", request.url)
        self.assertEqual(request.meta["viking_id"], "auction-1")
        self.assertEqual(request.meta["page"], 0)
        self.assertEqual(request.headers["x-algolia-api-key"].decode(), "real-key")

    def test_parse_lots_page_uses_nb_pages_for_followup_requests(self):
        response = self.make_json_response(
            {
                "hits": [],
                "nbPages": 3,
            },
            meta={
                "viking_id": "auction-1",
                "token": None,
                "algolia_api_key": "real-key",
                "page": 0,
            },
        )

        requests = list(self.spider.parse_lots_page(response))
        pages = [json.loads(request.body.decode("utf-8"))["page"] for request in requests]

        self.assertEqual(pages, [1, 2])

    def test_parse_lots_page_uses_common_db_id_but_raw_lot_card_id(self):
        response = self.make_json_response(
            {
                "hits": [
                    {
                        "objectID": "lot-raw-1",
                        "auctionId": "auction-1",
                        "title": "Producer A 2001 (1 BT75)",
                        "departments": ["Wine"],
                        "currency": "GBP",
                        "lowEstimate": 100,
                        "highEstimate": 200,
                        "Region": ["Bordeaux"],
                        "Country": ["France"],
                        "Winery": ["Producer A"],
                        "Vintage": ["2001"],
                        "Spirit Bottle Size": [],
                        "Wine Type": ["Red"],
                        "slug": "/en/buy/auction/2025/test/producer-a-2001",
                    }
                ],
                "nbPages": 1,
            },
            meta={
                "viking_id": "auction-1",
                "token": None,
                "algolia_api_key": "real-key",
                "page": 0,
            },
        )

        requests = list(self.spider.parse_lots_page(response))

        self.assertEqual(len(requests), 1)
        lot_card_request = requests[0]
        body = json.loads(lot_card_request.body.decode("utf-8"))
        self.assertEqual(body["variables"]["lotIds"], ["lot-raw-1"])
        self.assertEqual(
            lot_card_request.meta["lots"][0]["external_id"],
            "auction-1_lot-raw-1",
        )
        self.assertEqual(
            lot_card_request.meta["lot_items"][0]["lot_id"],
            "auction-1_lot-raw-1",
        )
        self.assertEqual(
            lot_card_request.meta["lot_card_ids_by_external_id"],
            {"auction-1_lot-raw-1": "lot-raw-1"},
        )

    def test_parse_viking_ids_uses_graphql_key_request_without_playwright(self):
        response = self.make_json_response(
            {
                "asset-1": {
                    "vikingId": "auction-1",
                    "url": "https://www.sothebys.com/en/buy/auction/2026/test-sale",
                }
            }
        )
        self.spider.check_exists = lambda _id, _type: False

        requests = list(self.spider.parse_viking_ids(response))

        self.assertEqual(len(requests), 2)
        key_request = requests[1]
        body = json.loads(key_request.body.decode("utf-8"))
        self.assertEqual(body["operationName"], "AlgoliaSearchKeyQuery")
        self.assertEqual(key_request.meta["viking_id"], "auction-1")
        self.assertEqual(key_request.meta["url"], "https://www.sothebys.com/en/buy/auction/2026/test-sale")
        self.assertNotIn("playwright", key_request.meta)

    def test_parse_viking_ids_filters_to_target_auction_ids(self):
        original_target_ids = sothebys_module.TARGET_AUCTION_IDS
        sothebys_module.TARGET_AUCTION_IDS = {"auction-2"}
        try:
            response = self.make_json_response(
                {
                    "asset-1": {
                        "vikingId": "auction-1",
                        "url": "https://www.sothebys.com/en/buy/auction/2026/skipped-sale",
                    },
                    "asset-2": {
                        "vikingId": "auction-2",
                        "url": "https://www.sothebys.com/en/buy/auction/2026/target-sale",
                    },
                }
            )
            self.spider.check_exists = lambda _id, _type: False

            requests = list(self.spider.parse_viking_ids(response))

            self.assertEqual(len(requests), 2)
            auction_request_body = json.loads(requests[0].body.decode("utf-8"))
            self.assertEqual(auction_request_body["variables"]["id"], "auction-2")
            self.assertEqual(requests[0].meta.get("url"), "https://www.sothebys.com/en/buy/auction/2026/target-sale")
            self.assertEqual(requests[1].meta.get("viking_id"), "auction-2")
        finally:
            sothebys_module.TARGET_AUCTION_IDS = original_target_ids

    def test_parse_lot_api_response_handles_missing_is_sold_and_keeps_lwin(self):
        lot = LotItem()
        lot["external_id"] = "auction-1_lot-raw-1"
        lot["auction_id"] = "auction-1"
        lot["lot_name"] = "Producer A 2001 (1 BT75)"
        lot["region"] = "Bordeaux"
        lot["sub_region"] = "Pauillac"
        lot["country"] = "France"

        lot_detail = LotDetailItem()
        lot_detail["lot_id"] = "auction-1_lot-raw-1"
        lot_detail["lot_producer"] = "Producer A"
        lot_detail["vintage"] = "2001"
        lot_detail["unit_format"] = "BT75"
        lot_detail["wine_colour"] = "Red"

        combined = CombinedLotItem()
        combined["lot"] = lot
        combined["lot_items"] = lot_detail

        response = self.make_json_response(
            {
                "data": {
                    "auction": {
                        "lot_ids": [
                            {
                                "lotId": "lot-raw-1",
                                "bidState": {
                                    "startingBid": {"amount": 100},
                                    "sold": {"__typename": "ResultHidden"},
                                    "closingTime": "2026-01-01T00:00:00Z",
                                },
                            }
                        ]
                    }
                }
            },
            meta={
                "lots": [lot],
                "lot_items": [lot_detail],
                "combined_lot_items": [combined],
                "lot_card_ids_by_external_id": {"auction-1_lot-raw-1": "lot-raw-1"},
            },
        )

        results = list(self.spider.parse_lot_api_response(response))

        self.assertIs(results[0], lot)
        self.assertEqual(lot["start_price"], 100)
        self.assertFalse(lot["sold"])
        self.assertEqual(lot["sold_date"], "2026-01-01T00:00:00Z")
        self.assertIs(results[1], lot_detail)
        self.assertEqual(results[2].url, "http://localhost:5000/match")

    def test_handle_lwin_response_reads_wrapped_match_payload(self):
        lot = LotItem()
        lot["external_id"] = "auction-1_lot-raw-1"

        response = self.make_json_response(
            {
                "meta": {"count": None},
                "data": {
                    "matched": "exact_match",
                    "lwin_code": [1234567],
                    "lwin_11_code": [12345672001],
                    "match_score": [0.98],
                    "match_item": [{"display_name": "Producer A 2001"}],
                },
            },
            meta={"item": lot},
        )

        results = list(self.spider.handle_lwin_response(response))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lot_id"], "auction-1_lot-raw-1")
        self.assertEqual(results[0]["matched"], "exact_match")
        self.assertEqual(results[0]["lwin"], [1234567])
        self.assertEqual(results[0]["lwin_11"], [12345672001])
        self.assertEqual(results[0]["match_score"], [0.98])
        self.assertEqual(
            json.loads(results[0]["match_item"]),
            [{"display_name": "Producer A 2001"}],
        )


class TestSothebysDiscovery(unittest.TestCase):
    def test_parse_schedules_all_result_pages_from_page_count(self):
        spider = SothebysSpider.__new__(SothebysSpider)
        response = HtmlResponse(
            url=RESULTS_URL,
            body=(
                b"<html><li class='SearchModule-pageCounts'>"
                b"<span data-page-count>3</span>"
                b"</li></html>"
            ),
            encoding="utf-8",
        )

        requests = list(spider.parse(response))

        self.assertEqual(len(requests), 3)
        self.assertEqual([request.url.rsplit("p=", 1)[1] for request in requests], ["1", "2", "3"])


if __name__ == "__main__":
    unittest.main()
