from __future__ import annotations

import re
import unittest
import requests
from unittest.mock import Mock
from scrapy.http import HtmlResponse, Request, Response
from tests.utils import live_html
from wine_spider.items import LotDetailItem, LotItem
from wine_spider.helpers import unit_format_to_volume
from wine_spider.exceptions import NoPreDefinedVolumeIdentifierException
from wine_spider.spiders.baghera import BagheraSpider

ARCHIVE_URL = "https://www.bagherawines.auction/en/catalogue/archive"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class TestBagheraArchivePage(unittest.TestCase):
    """Verify the Baghera archive page structure is still parseable."""

    @classmethod
    def setUpClass(cls):
        cls.response = live_html(ARCHIVE_URL, headers=HEADERS, timeout=20)

    def test_page_loads(self):
        self.assertIsNotNone(self.response.body)
        self.assertGreater(len(self.response.body), 0)

    def test_auction_links_found(self):
        links = self.response.css("div.col-8 a::attr(href)").getall()
        self.assertGreater(len(links), 0, "No auction links found — selector 'div.col-8 a' may have changed")

    def test_auction_links_are_catalogue_urls(self):
        links = self.response.css("div.col-8 a::attr(href)").getall()
        for link in links[:5]:
            self.assertIn("catalogue", link, f"Unexpected link format: {link}")


class TestBagheraAuctionPage(unittest.TestCase):
    """Verify a Baghera auction page can still be parsed for lots."""

    @classmethod
    def setUpClass(cls):
        # Get the first auction URL from the archive page
        archive = live_html(ARCHIVE_URL, headers=HEADERS, timeout=20)
        links = archive.css("div.col-8 a::attr(href)").getall()
        if not links:
            raise unittest.SkipTest("No auction links found on archive page")

        # Use the first past auction
        first_link = links[0]
        if not first_link.startswith("http"):
            first_link = "https://www.bagherawines.auction" + first_link

        cls.auction_url = first_link
        cls.response = live_html(first_link, headers=HEADERS, timeout=20)

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_auction_info_section_exists(self):
        auction_info = self.response.css("ul.infos.text-uppercase")
        self.assertIsNotNone(
            auction_info.get(),
            "Selector 'ul.infos.text-uppercase' returned nothing — page structure may have changed",
        )

    def test_auction_id_extractable(self):
        auction_info = self.response.css("ul.infos.text-uppercase")
        id_text = auction_info.css("li:nth-child(4)::text").get()
        self.assertIsNotNone(id_text, "Auction ID text selector 'li:nth-child(4)' returned None")
        auction_id = "".join(id_text.strip().split(" ")[1:])
        self.assertNotEqual(auction_id, "", "Parsed auction_id is empty")

    def test_lot_list_container_exists(self):
        lots = self.response.css("div#liste_lots div.lot_item")
        self.assertGreater(
            len(lots), 0,
            "Selector 'div#liste_lots div.lot_item' returned no lots — page structure may have changed",
        )

    def test_lot_name_extractable(self):
        lots = self.response.css("div#liste_lots div.lot_item")
        for lot_html in lots[:5]:
            name = lot_html.css("h3 span::text").get()
            self.assertIsNotNone(name, "Lot name selector 'h3 span::text' returned None")
            self.assertNotEqual(name.strip(), "")

    def test_lot_unit_format_extractable(self):
        lots = self.response.css("div#liste_lots div.lot_item")
        for lot_html in lots[:5]:
            lot_info = lot_html.css("div.caracteristiques table tbody")
            unit_format = lot_info.css("tr:nth-child(1) td:nth-child(1)::text").get()
            self.assertIsNotNone(
                unit_format,
                "Lot unit format selector 'tr:nth-child(1) td:nth-child(1)::text' returned None",
        )

    def test_lot_estimate_extractable(self):
        lots = self.response.css("div#liste_lots div.lot_item")
        for lot_html in lots[:5]:
            lot_info = lot_html.css("div.caracteristiques table tbody")
            low = lot_info.css("tr:nth-last-child(2) span.estimation_basse_ori::text").get()
            high = lot_info.css("tr:nth-last-child(1) span.estimation_haute_ori::text").get()
            # At least one estimate should be present
            self.assertTrue(
                low is not None or high is not None,
                "Neither low nor high estimate selector returned a value",
            )

    def test_lot_external_id_extractable(self):
        lots = self.response.css("div#liste_lots div.lot_item")
        for lot_html in lots[:5]:
            ext_id = lot_html.css("a.lien-lot::attr(href)").get()
            self.assertIsNotNone(ext_id, "Lot href selector 'a.lien-lot' returned None")
            lot_id = ext_id.split("/")[-1]
            self.assertNotEqual(lot_id, "")

    def test_currency_selector_present(self):
        currency = self.response.css(
            "select.form-control#change_devise option[selected]::text"
        ).get()
        self.assertIsNotNone(
            currency,
            "Currency selector returned None — check 'select.form-control#change_devise option[selected]'",
            )


class TestBagheraPdfParsing(unittest.TestCase):
    def test_parse_pdf_yields_lots_after_applying_sale_results(self):
        class StubPdfParser:
            def parse(self, body):
                return "1 123"

        spider = BagheraSpider.__new__(BagheraSpider)
        spider.pdf_parser = StubPdfParser()

        lot_item = LotItem(
            external_id="#122_lot-1",
            auction_id="#122",
            lot_name="Test wine",
            unit=1,
            original_currency="CHF",
            low_estimate=100,
            high_estimate=200,
            success=True,
            url="https://example.com/lot-1",
        )
        lots = {
            "1": {
                "lot_item": lot_item,
                "lot_detail_info": {
                    "lot_producer": ["Producer"],
                    "vintage": ["2000"],
                    "unit_format": ["bottle"],
                    "wine_colour": ["red"],
                },
            }
        }
        request = Request("https://example.com/results.pdf", meta={"lots": lots})
        response = Response(
            url="https://example.com/results.pdf",
            body=b"%PDF",
            request=request,
        )

        items = list(spider.parse_pdf(response))

        self.assertGreaterEqual(len(items), 2)
        self.assertEqual(items[0]["external_id"], "#122_lot-1")
        self.assertEqual(items[0]["end_price"], "123")
        self.assertEqual(items[1]["lot_id"], "#122_lot-1")


class TestBagheraFilterFailures(unittest.TestCase):
    def make_spider(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        spider.baghera_client = Mock()
        spider.baghera_client.get_filtered_auction_url.side_effect = (
            lambda original_url, filter_name, search_value: (
                f"{original_url}?{filter_name}={search_value}"
            )
        )
        return spider

    def make_lots(self):
        lot_item = LotItem(
            external_id="#122_lot-1",
            auction_id="#122",
            lot_name="Test wine",
            unit=1,
            original_currency="CHF",
            low_estimate=100,
            high_estimate=200,
            success=True,
            url="https://example.com/lot-1",
        )
        return {
            "1": {
                "lot_item": lot_item,
                "lot_detail_info": {
                    "lot_producer": ["Producer"],
                    "vintage": ["2000"],
                    "unit_format": ["bottle"],
                    "wine_colour": ["red"],
                },
            }
        }

    def make_filter_response(self, status=500, filters=None):
        request = Request(
            "https://www.bagherawines.auction/en/catalogue/voir/177?region=bad",
            meta={
                "original_url": "https://www.bagherawines.auction/en/catalogue/voir/177",
                "current_filter": "region",
                "current_data": "Bordeaux",
                "filters": filters if filters is not None else {},
                "lots": self.make_lots(),
                "processed_lots": [],
                "pdf_url": None,
            },
        )
        return HtmlResponse(
            url=request.url,
            request=request,
            status=status,
            body=b"",
            encoding="utf-8",
        )

    def test_failed_filter_response_continues_to_next_filter(self):
        spider = self.make_spider()
        response = self.make_filter_response(
            status=500,
            filters={
                "region": [],
                "lot_producer": [("yquem", "Yquem")],
            },
        )

        results = list(spider.parse_filters(response))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertIn("lot_producer=yquem", results[0].url)
        self.assertEqual(results[0].meta["handle_httpstatus_list"], [400, 403, 429, 500, 502, 503, 504])

    def test_failed_last_filter_yields_base_lots(self):
        spider = self.make_spider()
        response = self.make_filter_response(status=500, filters={})

        results = list(spider.parse_filters(response))

        self.assertTrue(any(isinstance(item, LotItem) for item in results))
        self.assertEqual(results[0]["external_id"], "#122_lot-1")

    def test_filter_requests_do_not_retry_known_server_filter_errors(self):
        spider = self.make_spider()
        lots = self.make_lots()

        request = spider.next_filter_request(
            original_url="https://www.bagherawines.auction/en/catalogue/voir/177",
            filters={"region": [("Bordeaux", "Bordeaux")]},
            lots=lots,
            processed_lots=[],
            pdf_url=None,
        )

        self.assertTrue(request.dont_filter)
        self.assertTrue(request.meta["dont_retry"])
        self.assertIn(500, request.meta["handle_httpstatus_list"])

    def test_final_pdf_request_allows_duplicate_sale_results_url(self):
        spider = self.make_spider()
        lots = self.make_lots()

        results = list(
            spider.finalize_filtered_lots(
                original_url="https://www.bagherawines.auction/en/catalogue/voir/177",
                lots=lots,
                pdf_url="https://www.bagherawines.auction/results.pdf",
            )
        )

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertTrue(results[0].dont_filter)
        self.assertIs(results[0].meta["lots"], lots)

    def test_finalization_requests_detail_fallback_for_missing_producer(self):
        spider = self.make_spider()
        lots = self.make_lots()
        lots["1"]["lot_detail_info"]["lot_producer"] = []

        results = list(
            spider.finalize_filtered_lots(
                original_url="https://www.bagherawines.auction/en/catalogue/voir/177",
                lots=lots,
                pdf_url="https://www.bagherawines.auction/results.pdf",
            )
        )

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertEqual(results[0].url, "https://example.com/lot-1")
        self.assertEqual(results[0].callback.__name__, "parse_detail_fallback")
        self.assertEqual(results[0].meta["pending_detail_sequence_ids"], [])
        self.assertEqual(results[0].meta["pdf_url"], "https://www.bagherawines.auction/results.pdf")


class TestBagheraDefensiveLotParsing(unittest.TestCase):
    def make_spider(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        spider.auction_client = Mock()
        spider.backfill_auction_ids = set()
        spider.check_auction_exists = Mock(return_value=False)
        spider.parse_auction = Mock(return_value=[])
        spider.next_filter_request = Mock(return_value=None)
        spider.finalize_filtered_lots = BagheraSpider.finalize_filtered_lots.__get__(spider, BagheraSpider)
        spider.yield_items = BagheraSpider.yield_items.__get__(spider, BagheraSpider)
        return spider

    def test_parse_auction_page_uses_sequence_name_when_lot_title_is_empty(self):
        spider = self.make_spider()
        html = """
        <ul class="infos text-uppercase">
          <li></li><li><span>June 26, 2025 (Europe/Paris)</span></li><li></li><li>Auction #99</li>
        </ul>
        <h1>Wine o'clock Geneva #99</h1>
        <select class="form-control" id="change_devise"><option selected>CHF</option></select>
        <div id="liste_lots">
          <div class="lot_item">
            <p class="numero mb0">1</p>
            <a class="lien-lot" href="https://www.bagherawines.auction/en/lot/voir/52205"></a>
            <h3><span></span></h3>
            <div class="caracteristiques"><table><tbody>
              <tr><td>Magnum(S):</td><td><span>1</span></td></tr>
              <tr><td>Estimate:</td><td><span class="estimation_basse_ori">0</span></td></tr>
              <tr><td></td><td><span class="estimation_haute_ori">0</span></td></tr>
            </tbody></table></div>
          </div>
        </div>
        """
        request = Request(
            "https://www.bagherawines.auction/en/catalogue/voir/145",
            meta={"original_url": "https://www.bagherawines.auction/en/catalogue/voir/145"},
        )
        response = HtmlResponse(
            url=request.url,
            request=request,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse_auction_page(response))
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        lot = results[0].meta["lots"]["1"]["lot_item"]

        self.assertEqual(lot["lot_name"], "Lot 1")

    def test_parse_lot_page_without_detail_section_still_yields_base_lot(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        lot_item = LotItem(
            external_id="#99_52205",
            auction_id="#99",
            lot_name="Lot 1",
            unit=1,
            original_currency="CHF",
            low_estimate=0,
            high_estimate=0,
            success=True,
            url="https://www.bagherawines.auction/en/lot/voir/52205",
        )
        request = Request(
            "https://www.bagherawines.auction/en/lot/voir/52205",
            meta={
                "lot_item": lot_item,
                "sequence_external_id": "1",
                "pdf_url": None,
            },
        )
        response = HtmlResponse(
            url=request.url,
            request=request,
            body=b"<html><h1>Lot detail</h1></html>",
            encoding="utf-8",
        )

        results = list(spider.parse_lot_page(response))

        self.assertEqual(results, [lot_item])

    def test_single_lot_pdf_request_allows_duplicate_sale_results_url(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        lot_item = LotItem(
            external_id="#99_52205",
            auction_id="#99",
            lot_name="Lot 1",
            unit=1,
            original_currency="CHF",
            low_estimate=0,
            high_estimate=0,
            success=True,
            url="https://www.bagherawines.auction/en/lot/voir/52205",
        )

        results = list(
            spider.yield_single_lot_items(
                lot_item,
                [],
                "1",
                pdf_url="https://www.bagherawines.auction/results.pdf",
            )
        )

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertTrue(results[0].dont_filter)
        self.assertIs(results[0].meta["lot_item"], lot_item)

    def test_parse_lot_page_detail_pdf_request_allows_duplicate_sale_results_url(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        lot_item = LotItem(
            external_id="#99_52205",
            auction_id="#99",
            lot_name="Lot 1",
            unit=1,
            original_currency="CHF",
            low_estimate=0,
            high_estimate=0,
            success=True,
            url="https://www.bagherawines.auction/en/lot/voir/52205",
        )
        html = """
        <span class="ecart style7">Details</span>
        <div class="row lot_mixte_item">
          <div class="information_label">Vintage</div><div>2000</div>
          <div class="information_label">Producer</div><div>Producer</div>
          <div class="information_label">Format</div><div>Bottle</div>
          <div class="information_label">Type</div><div>Red wine</div>
          <div class="information_label">Quantity</div><div>1</div>
          <div class="information_label">Nature</div><div>Wine</div>
          <div class="information_label">Area</div><div>Bordeaux</div>
          <div class="information_label">Subdivision</div><div>Medoc</div>
          <div class="information_label">Country of origin</div><div>France</div>
        </div>
        """
        request = Request(
            "https://www.bagherawines.auction/en/lot/voir/52205",
            meta={
                "lot_item": lot_item,
                "sequence_external_id": "1",
                "pdf_url": "https://www.bagherawines.auction/results.pdf",
            },
        )
        response = HtmlResponse(
            url=request.url,
            request=request,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse_lot_page(response))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertTrue(results[0].dont_filter)
        self.assertIs(results[0].meta["lot_item"], lot_item)

    def test_parse_lot_page_reads_flat_label_value_detail_layout(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        lot_item = LotItem(
            external_id="#kipling8_44742",
            auction_id="#Kipling#8",
            lot_name="Penfolds, Grange Bin 95 - 2003",
            unit=3,
            original_currency="CHF",
            low_estimate=100,
            high_estimate=200,
            success=True,
            url="https://www.bagherawines.auction/en/lot/voir/44742",
        )
        html = """
        <div class="information_label">Country of origin</div><div>Australia</div>
        <div class="information_label">Producer</div><div>Penfolds</div>
        <div class="information_label">Vintage</div><div>2003</div>
        <div class="information_label">Type</div><div>Red wine</div>
        <div class="information_label">Format</div><div>Mganums</div>
        <div class="information_label">Quantity</div><div>3</div>
        <div class="information_label">Nature</div><div>Wine</div>
        <div class="information_label">Area</div><div>South Australia</div>
        """
        request = Request(
            "https://www.bagherawines.auction/en/lot/voir/44742",
            meta={
                "lot_item": lot_item,
                "sequence_external_id": "96",
                "pdf_url": None,
            },
        )
        response = HtmlResponse(
            url=request.url,
            request=request,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse_lot_page(response))
        parsed_lot = next(result for result in results if isinstance(result, LotItem))
        detail = next(result for result in results if isinstance(result, LotDetailItem))

        self.assertEqual(parsed_lot["volume"], 4500)
        self.assertEqual(parsed_lot["lot_type"], ["Wine"])
        self.assertEqual(parsed_lot["region"], "South Australia")
        self.assertEqual(parsed_lot["country"], "Australia")
        self.assertEqual(detail["lot_producer"], "Penfolds")
        self.assertEqual(detail["vintage"], "2003")
        self.assertEqual(detail["unit_format"], "magnum")
        self.assertEqual(detail["wine_colour"], "Red wine")

    def test_detail_fallback_reads_macallan_spirits_detail_layout(self):
        spider = BagheraSpider.__new__(BagheraSpider)
        lot_item = LotItem(
            external_id="#86_46700",
            auction_id="#86",
            lot_name="The Macallan, Decanter Series 'Black Release' Single Malt Scotch Whisky",
            unit=1,
            original_currency="CHF",
            low_estimate=3400,
            high_estimate=6800,
            success=True,
            url="https://www.bagherawines.auction/en/lot/voir/46700",
        )
        lots = {
            "1": {
                "lot_item": lot_item,
                "lot_detail_info": {
                    "lot_producer": [],
                    "vintage": [],
                    "unit_format": ["bottle"],
                    "wine_colour": [],
                },
            }
        }
        html = """
        <div class="information_label">Country of origin</div><div>Scotland</div>
        <div class="information_label">Area</div><div>Highlands</div>
        <div class="information_label">Producer</div><div>The Macallan</div>
        <div class="information_label">Vintage</div><div>NV</div>
        <div class="information_label">Type</div><div>Whisky</div>
        <div class="information_label">Format</div><div>Bottle(s)</div>
        <div class="information_label">Quantity</div><div>1</div>
        <div class="information_label">Nature</div><div>Spirits</div>
        <div class="information_label">Capacity</div><div>70cl</div>
        """
        request = Request(
            "https://www.bagherawines.auction/en/lot/voir/46700",
            meta={
                "original_url": "https://www.bagherawines.auction/en/catalogue/voir/125",
                "lots": lots,
                "sequence_external_id": "1",
                "pending_detail_sequence_ids": [],
                "pdf_url": "https://www.bagherawines.auction/results.pdf",
            },
        )
        response = HtmlResponse(
            url=request.url,
            request=request,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

        results = list(spider.parse_detail_fallback(response))

        self.assertEqual(lot_item["volume"], 700)
        self.assertEqual(lot_item["lot_type"], ["Spirits"])
        self.assertEqual(lot_item["region"], "Highlands")
        self.assertEqual(lot_item["country"], "Scotland")
        self.assertEqual(lots["1"]["lot_detail_info"]["lot_producer"], ["The Macallan"])
        self.assertEqual(lots["1"]["lot_detail_info"]["vintage"], ["NV"])
        self.assertEqual(lots["1"]["lot_detail_info"]["unit_format"], ["70cl"])
        self.assertEqual(lots["1"]["lot_detail_info"]["wine_colour"], ["Whisky"])
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Request)
        self.assertEqual(results[0].url, "https://www.bagherawines.auction/results.pdf")


if __name__ == "__main__":
    unittest.main()
