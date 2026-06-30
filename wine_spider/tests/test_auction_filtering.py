from __future__ import annotations

import os
import asyncio
import json
import unittest
from unittest.mock import Mock

from scrapy.http import HtmlResponse, Request, TextResponse

from wine_spider.items import AuctionItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.spiders.baghera import BagheraSpider
from wine_spider.spiders.bonhams import BonhamsSpider
from wine_spider.spiders.christies import ChristiesSpider
from wine_spider.spiders.steinfels import SteinfelsSpider
from wine_spider.spiders.sylvies import SylviesSpider
from wine_spider.spiders.tajan import TajanSpider
from wine_spider.spiders.wineauctioneer import (
    WineAuctioneerSpider,
    auction_id_from_listing_link,
    normalize_auction_id_for_url_filter,
)
from wine_spider.spiders.zachys import ZachysSpider
from wine_spider.services import ZachysClient


class DummyAuctionSpider(BaseAuctionSpider):
    name = "dummy_auction_spider"


def make_json_response(url: str = "https://example.test/api") -> TextResponse:
    request = Request(url=url)
    return TextResponse(url=url, request=request, body=b"{}", encoding="utf-8")


def make_html_response(html: str, url: str = "https://example.test/") -> HtmlResponse:
    request = Request(url=url)
    return HtmlResponse(url=url, request=request, body=html.encode("utf-8"), encoding="utf-8")


async def collect_async(async_iterable):
    return [item async for item in async_iterable]


class BaseAuctionSpiderFilteringTests(unittest.TestCase):
    def setUp(self):
        self.original_full_fetch = os.environ.get("FULL_FETCH")

    def tearDown(self):
        if self.original_full_fetch is None:
            os.environ.pop("FULL_FETCH", None)
        else:
            os.environ["FULL_FETCH"] = self.original_full_fetch

    def test_should_skip_existing_auction_when_full_fetch_disabled(self):
        os.environ["FULL_FETCH"] = "False"
        spider = DummyAuctionSpider()
        auction_client = Mock()
        auction_client.get_by_external_id.return_value = object()
        lot_client = Mock()
        lot_client.has_lots_for_auction.return_value = True

        self.assertTrue(spider.should_skip_existing_auction("auction-1", auction_client, lot_client))
        auction_client.get_by_external_id.assert_called_once_with("auction-1")
        lot_client.has_lots_for_auction.assert_called_once_with("auction-1")

    def test_should_not_skip_existing_auction_without_lots(self):
        os.environ["FULL_FETCH"] = "False"
        spider = DummyAuctionSpider()
        auction_client = Mock()
        auction_client.get_by_external_id.return_value = object()
        lot_client = Mock()
        lot_client.has_lots_for_auction.return_value = False

        self.assertFalse(spider.should_skip_existing_auction("auction-1", auction_client, lot_client))
        auction_client.get_by_external_id.assert_called_once_with("auction-1")
        lot_client.has_lots_for_auction.assert_called_once_with("auction-1")

    def test_should_not_skip_existing_auction_when_full_fetch_enabled(self):
        os.environ["FULL_FETCH"] = "True"
        spider = DummyAuctionSpider()
        auction_client = Mock()
        lot_client = Mock()

        self.assertFalse(spider.should_skip_existing_auction("auction-1", auction_client, lot_client))
        auction_client.get_by_external_id.assert_not_called()
        lot_client.has_lots_for_auction.assert_not_called()


class CustomAuctionFilteringTests(unittest.TestCase):
    def test_christies_refetches_existing_auction_when_lots_are_missing(self):
        from wine_spider.spiders import christies

        original_full_fetch = christies.FULL_FETCH
        original_auctions_client = christies.auctions_client
        original_lots_client = christies.lots_client
        try:
            christies.FULL_FETCH = "False"
            christies.auctions_client = Mock()
            christies.auctions_client.get_by_external_id.return_value = object()
            christies.lots_client = Mock()
            christies.lots_client.has_lots_for_auction.return_value = False
            spider = ChristiesSpider.__new__(ChristiesSpider)
            html = """
            <script>
            window.chrComponents.calendar = {"data":{"events":[{"filter_ids":"category_14","title_txt":"Fine Wine","location_txt":"London","start_date":"2024-01-01T00:00:00","end_date":"2024-01-02T00:00:00","is_live":false,"landing_url":"https://www.christies.com/en/auction/fine-wine-12345/","subtitle_txt":"Sale number 6789"}]}};
            </script>
            """

            results = list(spider.parse(make_html_response(html, "https://www.christies.com/en/results")))

            self.assertTrue(any(isinstance(result, AuctionItem) for result in results))
            self.assertTrue(any(isinstance(result, Request) for result in results))
            christies.lots_client.has_lots_for_auction.assert_called_once_with("12345#6789")
        finally:
            christies.FULL_FETCH = original_full_fetch
            christies.auctions_client = original_auctions_client
            christies.lots_client = original_lots_client

    def test_sothebys_existing_auction_without_lots_is_not_treated_as_complete(self):
        from wine_spider.spiders import sothebys

        original_auctions_client = sothebys.auctions_client
        original_lots_client = sothebys.lots_client
        try:
            sothebys.auctions_client = Mock()
            sothebys.auctions_client.get_by_external_id.return_value = object()
            sothebys.lots_client = Mock()
            sothebys.lots_client.has_lots_for_auction.return_value = False
            spider = sothebys.SothebysSpider.__new__(sothebys.SothebysSpider)

            self.assertFalse(spider.check_exists("auction-1", "auction"))
            sothebys.lots_client.has_lots_for_auction.assert_called_once_with("auction-1")
        finally:
            sothebys.auctions_client = original_auctions_client
            sothebys.lots_client = original_lots_client


class BonhamsAuctionFilteringTests(unittest.TestCase):
    def test_custom_settings_are_conservative_for_bonhams_api(self):
        settings = BonhamsSpider.custom_settings

        self.assertLessEqual(settings["CONCURRENT_REQUESTS"], 2)
        self.assertLessEqual(settings["CONCURRENT_REQUESTS_PER_DOMAIN"], 2)
        self.assertGreaterEqual(settings["DOWNLOAD_DELAY"], 1)
        self.assertGreaterEqual(settings["RETRY_TIMES"], 8)

    def test_backfill_auction_ids_limit_scheduled_lot_requests(self):
        spider = BonhamsSpider()
        spider.backfill_auction_ids = {"target"}
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=False)
        spider.bonhams_client = Mock()
        spider.bonhams_client.api_url = "https://api01.bonhams.com/search"
        spider.bonhams_client.headers = {}
        spider.bonhams_client.parse_auction_api_response.return_value = [
            AuctionItem(external_id="skip-me", auction_title="Skip"),
            AuctionItem(external_id="target", auction_title="Target"),
        ]
        spider.bonhams_client.get_lot_search_payload.return_value = {"searches": []}

        results = list(spider.parse(make_json_response()))

        yielded_auction_ids = [
            result["external_id"]
            for result in results
            if isinstance(result, AuctionItem)
        ]
        lot_request_ids = [
            result.meta.get("auction_id")
            for result in results
            if isinstance(result, Request) and result.meta.get("auction_id")
        ]

        self.assertEqual(yielded_auction_ids, ["target"])
        self.assertEqual(lot_request_ids, ["target"])

    def test_existing_auction_does_not_stop_later_new_auctions(self):
        spider = BonhamsSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(side_effect=lambda auction_id, _client: auction_id == "existing")
        spider.bonhams_client = Mock()
        spider.bonhams_client.api_url = "https://api01.bonhams.com/search"
        spider.bonhams_client.headers = {}
        spider.bonhams_client.parse_auction_api_response.return_value = [
            AuctionItem(external_id="existing", auction_title="Existing"),
            AuctionItem(external_id="new", auction_title="New"),
        ]
        spider.bonhams_client.get_lot_search_payload.return_value = {"searches": []}

        results = list(spider.parse(make_json_response()))

        yielded_auction_ids = [
            result["external_id"]
            for result in results
            if isinstance(result, AuctionItem)
        ]
        lot_requests = [
            result
            for result in results
            if isinstance(result, Request) and result.meta.get("auction_id") == "new"
        ]

        self.assertEqual(yielded_auction_ids, ["new"])
        self.assertEqual(len(lot_requests), 1)

    def test_parse_schedules_next_auction_search_page_when_page_is_full(self):
        spider = BonhamsSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=True)
        spider.bonhams_client = Mock()
        spider.bonhams_client.api_url = "https://api01.bonhams.com/search"
        spider.bonhams_client.headers = {}
        spider.bonhams_client.parse_auction_api_response.return_value = [
            AuctionItem(external_id="existing", auction_title="Existing")
        ]
        spider.bonhams_client.get_auction_search_payload.return_value = {"searches": []}

        payload = {
            "results": [
                {
                    "hits": [{"document": {"id": str(i)}} for i in range(250)]
                }
            ]
        }
        request = Request(
            url="https://api01.bonhams.com/search",
            meta={"current_page": 1, "per_page": 250},
        )
        response = TextResponse(
            url=request.url,
            request=request,
            body=json.dumps(payload).encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse(response))

        next_page_requests = [
            result
            for result in results
            if isinstance(result, Request)
            and result.meta.get("current_page") == 2
        ]
        self.assertEqual(len(next_page_requests), 1)
        spider.bonhams_client.get_auction_search_payload.assert_called_once_with(
            page=2,
            per_page=250,
        )


class MissingAuctionFilteringTests(unittest.TestCase):
    def test_steinfels_skips_existing_auctions_from_api_list(self):
        spider = SteinfelsSpider()
        spider.auction_client = Mock()
        spider.should_skip_existing_auction = Mock(side_effect=lambda auction_id, _client: auction_id == "existing")
        spider.steinfels_client.parse_auction_api_response = Mock(
            return_value=(
                [
                    AuctionItem(external_id="existing", url="https://example.test?cat_id=old"),
                    AuctionItem(external_id="new", url="https://example.test?cat_id=new"),
                ],
                ["old", "new"],
            )
        )
        spider.steinfels_client.get_lot_api_url = Mock(return_value="https://example.test/lots")

        results = list(spider.parse(make_json_response()))

        yielded_auction_ids = [
            result["external_id"]
            for result in results
            if isinstance(result, AuctionItem)
        ]
        lot_requests = [
            result
            for result in results
            if isinstance(result, Request) and result.meta.get("auction_catalog_id") == "new"
        ]

        self.assertEqual(yielded_auction_ids, ["new"])
        self.assertEqual(len(lot_requests), 1)

    def test_steinfels_backfill_auction_ids_limit_scheduled_lot_requests(self):
        spider = SteinfelsSpider()
        spider.backfill_auction_ids = {"target"}
        spider.auction_client = Mock()
        spider.should_skip_existing_auction = Mock(return_value=False)
        spider.steinfels_client.parse_auction_api_response = Mock(
            return_value=(
                [
                    AuctionItem(external_id="skip-me", url="https://example.test?cat_id=old"),
                    AuctionItem(external_id="target", url="https://example.test?cat_id=new"),
                ],
                ["old", "new"],
            )
        )
        spider.steinfels_client.get_lot_api_url = Mock(return_value="https://example.test/lots")

        results = list(spider.parse(make_json_response()))

        yielded_auction_ids = [
            result["external_id"]
            for result in results
            if isinstance(result, AuctionItem)
        ]
        lot_requests = [
            result
            for result in results
            if isinstance(result, Request) and result.meta.get("auction_catalog_id") == "new"
        ]

        self.assertEqual(yielded_auction_ids, ["target"])
        self.assertEqual(len(lot_requests), 1)

    def test_sylvies_skips_existing_auctions_before_detail_request(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        spider.auction_client = Mock()
        spider.backfill_auction_ids = set()
        spider.should_skip_existing_auction = Mock(
            side_effect=lambda auction_id, _client: auction_id == "sylvies_january-2020"
        )
        html = """
        <div class="history">
          <a href="/en/auction/1">January 2020</a>
          <a href="/en/auction/2">February 2020</a>
        </div>
        """

        results = list(spider.parse(make_html_response(html, "https://www.sylvies.be/en/ended-auctions")))
        auction_requests = [result for result in results if isinstance(result, Request)]

        self.assertEqual(len(auction_requests), 1)
        self.assertEqual(auction_requests[0].meta["auction_id"], "sylvies_february-2020")

    def test_sylvies_backfill_auction_ids_limit_scheduled_requests(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        spider.auction_client = Mock()
        spider.backfill_auction_ids = {"sylvies_february-2020"}
        spider.should_skip_existing_auction = Mock(return_value=False)
        html = """
        <div class="history">
          <a href="/en/auction/1">January 2020</a>
          <a href="/en/auction/2">February 2020</a>
        </div>
        """

        results = list(spider.parse(make_html_response(html, "https://www.sylvies.be/en/ended-auctions")))
        auction_requests = [result for result in results if isinstance(result, Request)]

        self.assertEqual(len(auction_requests), 1)
        self.assertEqual(auction_requests[0].meta["auction_id"], "sylvies_february-2020")

    def test_baghera_backfill_auction_ids_skips_non_target_auction(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        spider.backfill_auction_ids = {"#target"}
        spider.check_auction_exists = Mock()
        html = """
        <ul class="infos text-uppercase">
          <li>ignored</li>
          <li><span>January 1, 2024 (Europe/Geneva)</span></li>
          <li>ignored</li>
          <li>Auction #skip</li>
        </ul>
        """
        response = make_html_response(
            html,
            "https://www.bagherawines.auction/en/catalogue/voir/177",
        )
        response.meta["original_url"] = response.url

        results = list(spider.parse_auction_page(response))

        self.assertEqual(results, [])
        spider.check_auction_exists.assert_not_called()

    def test_tajan_skips_existing_auctions_before_lot_page_request(self):
        spider = TajanSpider.__new__(TajanSpider)
        spider.auction_client = Mock()
        spider.should_skip_existing_auction = Mock(return_value=True)
        html = """
        <div id="plab__results-container">
          <div class="widget-event">
            <h2 class="event__title"><a href="https://www.tajan.com/en/auction/wine-sale/">Wine Sale</a></h2>
            <div class="event__date">Monday, January 1, 2024</div>
            <div class="event__time mb-0">10:00</div>
            <div class="event__location mb-0">Paris, France</div>
          </div>
        </div>
        """

        results = asyncio.run(collect_async(spider.parse(make_html_response(html, "https://www.tajan.com/en/past/"))))

        self.assertEqual(results, [])

    def test_zachys_skips_existing_auctions_before_lot_page_request(self):
        spider = ZachysSpider.__new__(ZachysSpider)
        spider.auction_client = Mock()
        spider.should_skip_existing_auction = Mock(return_value=True)
        spider.max_pages = 1
        html = """
        <script data-server="true">
        {"default":{"auctionRows":[{"id":"161","name":"Fine Sale","auction_seo_url":"Fine-Sale","start_date":"2026-06-25 17:35:10","end_date":"2026-06-26 19:36:58","cauction_listing_location":"Delaware"}]}}
        </script>
        """

        response = make_html_response(html, "https://bid.zachys.com/auctions?page=1&status=5")
        response.meta["current_page"] = 1
        results = asyncio.run(collect_async(spider.parse(response)))

        self.assertEqual(results, [])
        spider.should_skip_existing_auction.assert_called_once_with("zachys_161", spider.auction_client)

    def test_zachys_listing_schedules_past_catalog_links(self):
        spider = ZachysSpider.__new__(ZachysSpider)
        spider.auction_client = Mock()
        spider.should_skip_existing_auction = Mock(return_value=False)
        spider.zachys_client = ZachysClient()
        spider.max_pages = 1
        html = """
        <script data-server="true">
        {"default":{"auctionRows":[{"id":"161","name":"Fine & Rare Wines, Delaware, June 25 & 26","auction_seo_url":"Fine-Rare-Wines-Delaware-June-18-19","start_date":"2026-06-25 17:35:10","end_date":"2026-06-26 19:36:58","cauction_listing_location":"Delaware"}]}}
        </script>
        """

        response = make_html_response(html, "https://bid.zachys.com/auctions?page=1&status=5")
        response.meta["current_page"] = 1
        results = asyncio.run(collect_async(spider.parse(response)))

        self.assertEqual(len(results), 2)
        auction_item, catalog_request = results
        self.assertIsInstance(auction_item, AuctionItem)
        self.assertEqual(auction_item["external_id"], "zachys_161")
        self.assertEqual(auction_item["city"], "Delaware")
        self.assertEqual(auction_item["start_date"], "2026-06-25")
        self.assertEqual(auction_item["end_date"], "2026-06-26")
        self.assertIsInstance(catalog_request, Request)
        self.assertEqual(
            catalog_request.url,
            "https://bid.zachys.com/auctions/catalog/id/161/Fine-Rare-Wines-Delaware-June-18-19?items=100&page=1",
        )
        self.assertTrue(catalog_request.meta["playwright"])
        self.assertEqual(catalog_request.meta["auction_id"], "zachys_161")

    def test_wineauctioneer_skips_existing_auction_before_lot_requests(self):
        spider = WineAuctioneerSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=True)
        html = """
        <h1 class="page-title">January Wine Auction</h1>
        <div class="auction-info field-hstack">
          <div><div>01 January 2024</div></div>
          <div><div>ignored</div><div>02 January 2024</div></div>
        </div>
        <div class="auction-status auction-status-closed">Closed</div>
        <h3 class="teaser-title"><a href="/lot/1">Lot 1</a></h3>
        """

        results = list(spider.parse_auction(make_html_response(html, "https://wineauctioneer.com/wine-auctions/january/lots")))

        self.assertEqual(results, [])

    def test_wineauctioneer_parse_auction_schedules_all_first_page_lots(self):
        spider = WineAuctioneerSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=False)
        html = """
        <h1 class="page-title">January Wine Auction</h1>
        <div class="auction-info field-hstack">
          <div><div>01 January 2024</div></div>
          <div><div>ignored</div><div>02 January 2024</div></div>
        </div>
        <div class="auction-status auction-status-closed">Closed</div>
        <h3 class="teaser-title"><a href="/lot/1">Lot 1</a></h3>
        <h3 class="teaser-title"><a href="/lot/2">Lot 2</a></h3>
        """

        results = list(spider.parse_auction(make_html_response(html, "https://wineauctioneer.com/wine-auctions/january/lots")))
        lot_requests = [
            result
            for result in results
            if isinstance(result, Request) and result.callback == spider.parse_lot
        ]

        self.assertEqual([request.url for request in lot_requests], [
            "https://wineauctioneer.com/lot/1",
            "https://wineauctioneer.com/lot/2",
        ])

    def test_wineauctioneer_backfill_auction_ids_limit_scheduled_lot_requests(self):
        spider = WineAuctioneerSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=False)
        spider.backfill_auction_ids = {"target-auction"}
        html = """
        <h1 class="page-title">Skip Auction</h1>
        <div class="auction-info field-hstack">
          <div><div>01 January 2024</div></div>
          <div><div>ignored</div><div>02 January 2024</div></div>
        </div>
        <div class="auction-status auction-status-closed">Closed</div>
        <h3 class="teaser-title"><a href="/lot/1">Lot 1</a></h3>
        """

        results = list(spider.parse_auction(make_html_response(html, "https://wineauctioneer.com/wine-auctions/skip/lots")))

        self.assertEqual(results, [])
        spider.check_auction_exists.assert_not_called()

    def test_wineauctioneer_parse_skips_non_target_auction_links_before_request(self):
        spider = WineAuctioneerSpider()
        spider.backfill_auction_ids = {"target-auction"}
        spider.normalized_backfill_auction_ids = {"target-auction"}
        html = """
        <a class="btn" href="/wine-auctions/target-auction/lots">Target</a>
        <a class="btn" href="/wine-auctions/skip-auction/lots">Skip</a>
        """

        results = list(spider.parse(make_html_response(html, "https://wineauctioneer.com/wine-auctions")))
        auction_requests = [
            result
            for result in results
            if isinstance(result, Request) and "/wine-auctions/" in result.url
        ]

        self.assertEqual(
            [request.url for request in auction_requests],
            ["https://wineauctioneer.com/wine-auctions/target-auction/lots"],
        )

    def test_wineauctioneer_backfill_url_filter_matches_normalized_external_ids(self):
        assert auction_id_from_listing_link("/wine-auctions/December-2023-Auction/lots") == "december-2023-auction"
        assert normalize_auction_id_for_url_filter("icons-&-vintage-port-2019---3-day-auction") == (
            "icons-vintage-port-2019-3-day-auction"
        )

    def test_wineauctioneer_parse_follows_pagination_links_from_page(self):
        spider = WineAuctioneerSpider()
        html = """
        <a class="btn" href="/wine-auctions/january-2026-auction/lots">Lots</a>
        <a href="?page=0%2C2%2C0%2C0%2C0">3</a>
        """

        results = list(spider.parse(make_html_response(html, "https://wineauctioneer.com/wine-auctions")))
        pagination_requests = [
            result for result in results
            if isinstance(result, Request) and "page=0%2C2%2C0%2C0%2C0" in result.url
        ]

        self.assertEqual(len(pagination_requests), 1)

    def test_wineauctioneer_parse_auction_links_use_listing_navigation_headers(self):
        spider = WineAuctioneerSpider()
        html = """
        <a class="btn" href="/wine-auctions/january-2026-auction/lots">Lots</a>
        """

        results = list(spider.parse(make_html_response(html, "https://wineauctioneer.com/wine-auctions#past-auctions")))
        auction_request = next(result for result in results if isinstance(result, Request))

        self.assertEqual(
            auction_request.headers["referer"].decode(),
            "https://wineauctioneer.com/wine-auctions",
        )
        self.assertEqual(
            auction_request.meta["playwright_page_goto_kwargs"]["referer"],
            "https://wineauctioneer.com/wine-auctions",
        )
        self.assertEqual(auction_request.headers["sec-fetch-site"].decode(), "same-origin")
        self.assertEqual(auction_request.headers["sec-fetch-mode"].decode(), "navigate")

    def test_wineauctioneer_lot_requests_use_auction_page_as_playwright_referer(self):
        spider = WineAuctioneerSpider()
        spider.auction_client = Mock()
        spider.check_auction_exists = Mock(return_value=False)
        html = """
        <h1 class="page-title">January Wine Auction</h1>
        <div class="auction-info field-hstack">
          <div><div>01 January 2024</div></div>
          <div><div>ignored</div><div>02 January 2024</div></div>
        </div>
        <div class="auction-status auction-status-closed">Closed</div>
        <h3 class="teaser-title"><a href="/wine-lot/1/example">Lot 1</a></h3>
        """

        results = list(spider.parse_auction(make_html_response(
            html,
            "https://wineauctioneer.com/wine-auctions/january-wine-auction/lots",
        )))
        lot_request = next(
            result
            for result in results
            if isinstance(result, Request) and result.callback == spider.parse_lot
        )

        self.assertEqual(
            lot_request.meta["playwright_page_goto_kwargs"]["referer"],
            "https://wineauctioneer.com/wine-auctions/january-wine-auction/lots",
        )

    def test_wineauctioneer_parse_does_not_loop_listing_pagination(self):
        spider = WineAuctioneerSpider()
        html = """
        <a class="btn" href="/wine-auctions/january-2026-auction/lots">Lots</a>
        <a href="?page=0%2C1%2C0%2C0%2C0">2</a>
        <a href="?page=0%2C2%2C0%2C0%2C0">3</a>
        """

        results = list(spider.parse(make_html_response(
            html,
            "https://wineauctioneer.com/wine-auctions?page=0%2C1%2C0%2C0%2C0",
        )))
        pagination_requests = [
            result
            for result in results
            if isinstance(result, Request) and "page=0%2C" in result.url
        ]

        self.assertEqual([request.url for request in pagination_requests], [
            "https://wineauctioneer.com/wine-auctions?page=0%2C2%2C0%2C0%2C0",
        ])
        self.assertTrue(all(not request.dont_filter for request in pagination_requests))

    def test_wineauctioneer_keeps_playwright_resource_blocker_middleware(self):
        middlewares = WineAuctioneerSpider.custom_settings["DOWNLOADER_MIDDLEWARES"]

        self.assertIn(
            "wine_spider.middlewares.playwright_resource_blocker_middleware.PlaywrightResourceBlockerMiddleware",
            middlewares,
        )
        self.assertIn(
            "wine_spider.middlewares.wineauctioneer_login_middleware.WineauctioneerLoginMiddleware",
            middlewares,
        )


if __name__ == "__main__":
    unittest.main()
