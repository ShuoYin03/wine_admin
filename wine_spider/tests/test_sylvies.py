from __future__ import annotations

import unittest

from scrapy.http import HtmlResponse, Request

from wine_spider.items import LotDetailItem, LotItem
from wine_spider.helpers.sylvies.pdf_parser import parse_pdf_dates_from_text
from wine_spider.spiders.sylvies import SylviesSpider
from tests.utils import live_html

ENDED_AUCTIONS_URL = "https://www.sylvies.be/en/ended-auctions"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class TestSylviesEndedAuctionsPage(unittest.TestCase):
    """Verify the Sylvie's ended-auctions listing page is still parseable."""

    @classmethod
    def setUpClass(cls):
        cls.response = live_html(ENDED_AUCTIONS_URL, headers=HEADERS, timeout=20)

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_history_div_exists(self):
        history = self.response.css("div.history")
        self.assertIsNotNone(
            history.get(),
            "Selector 'div.history' returned nothing — page structure may have changed",
        )

    def test_auction_links_found(self):
        links = self.response.css('div.history a[href^="/en/auction/"]').getall()
        self.assertGreater(len(links), 0, "No auction links found matching 'a[href^=\"/en/auction/\"]'")

    def test_auction_links_contain_title_text(self):
        link_elements = self.response.css('div.history a[href^="/en/auction/"]')
        for el in link_elements[:5]:
            text = el.css("::text").get()
            self.assertIsNotNone(text)
            self.assertNotEqual(text.strip(), "")


class TestSylviesAuctionPage(unittest.TestCase):
    """Verify a Sylvie's auction page lot structure is still parseable."""

    @classmethod
    def setUpClass(cls):
        # Get the first real auction URL from the listing page
        listing = live_html(ENDED_AUCTIONS_URL, headers=HEADERS, timeout=20)
        links = listing.css('div.history a[href^="/en/auction/"]::attr(href)').getall()
        # Skip placeholder auction /0/ links
        valid_links = [l for l in links if "/en/auction/0/" not in l]
        if not valid_links:
            raise unittest.SkipTest("No valid auction links found on listing page")

        auction_path = valid_links[0]
        if not auction_path.startswith("http"):
            auction_path = "https://www.sylvies.be" + auction_path

        cls.auction_url = auction_path
        cls.response = live_html(auction_path, headers=HEADERS, timeout=20)

    def test_page_loads(self):
        self.assertGreater(len(self.response.body), 0)

    def test_auction_lots_container_exists(self):
        container = self.response.css("div.auction_lots")
        self.assertIsNotNone(
            container.get(),
            "Selector 'div.auction_lots' returned nothing — page structure may have changed",
        )

    def test_lot_items_found(self):
        lots = self.response.css("div.auction_lots div.auction_item")
        self.assertGreater(
            len(lots), 0,
            "Selector 'div.auction_item' returned no lots — page structure may have changed",
        )

    def test_lot_id_extractable(self):
        lots = self.response.css("div.auction_lots div.auction_item")
        for lot in lots[:5]:
            lot_class = lot.css("div.lot_item::attr(class)").get()
            self.assertIsNotNone(lot_class, "Lot class attribute 'div.lot_item::attr(class)' returned None")
            lot_id = lot_class.strip().split(" ")[-1].split("_")[-1].strip()
            self.assertNotEqual(lot_id, "")

    def test_lot_number_link_exists(self):
        lots = self.response.css("div.auction_lots div.auction_item")
        for lot in lots[:5]:
            link_text = lot.css("p.lot_nr a::text").get()
            self.assertIsNotNone(link_text, "Lot number link 'p.lot_nr a::text' returned None")

    def test_lot_estimate_present(self):
        lots = self.response.css("div.auction_lots div.auction_item")
        has_estimate = False
        for lot in lots[:10]:
            price_info = lot.css("div.large-2.columns.auction_infos")
            estimate = price_info.css("div.lot_estimate + p::text").get()
            if estimate:
                has_estimate = True
                break
        self.assertTrue(has_estimate, "No lot estimates found via 'div.lot_estimate + p::text'")

    def test_appellation_select_exists(self):
        appellation = self.response.css("div.multiselectbox_select.select_appelation")
        self.assertIsNotNone(
            appellation.get(),
            "Appellation selector 'div.multiselectbox_select.select_appelation' returned nothing",
        )

    def test_lot_description_extractable(self):
        lots = self.response.css("div.auction_lots div.auction_item")
        for lot in lots[:5]:
            sub_lots = lot.css("div.lot_item")
            for sub in sub_lots[:2]:
                desc = sub.css("div.lot_description::text").get()
                if desc and "|" in desc:
                    parts = desc.split("|")
                    self.assertGreaterEqual(len(parts), 2)
                    return  # found at least one valid description
        # If we get here without returning, just warn
        self.skipTest("No lot descriptions with '|' separator found in first 5 lots")


class TestSylviesSpiderParsing(unittest.TestCase):
    def make_response(self, html: str):
        request = Request(
            url="https://www.sylvies.be/en/auction/217",
            meta={
                "auction_id": "sylvies_february-2021",
                "auction_item": None,
            },
        )
        return HtmlResponse(
            url=request.url,
            request=request,
            body=html.encode("utf-8"),
            encoding="utf-8",
        )

    def test_parse_auction_uses_visible_lot_title_and_metadata(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation">
              <ul>
                <li class="multiselectbox_title"><label>Wines</label></li>
                <li><label>France (1)</label></li>
                <li class="sub">
                  <label>Bordeaux (1)</label>
                  <ul>
                    <li class="sub_sub"><label>Saint Estephe (1)</label></li>
                  </ul>
                </li>
                <li class="multiselectbox_title"><label>Spirits</label></li>
                <li><label>Whisky (1)</label></li>
                <li class="multiselectbox_title"><label>Port Sherry</label></li>
                <li><label>Port (1)</label></li>
              </ul>
            </div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>€100 - €200</p>
                  <div class="lot_my_bid"></div><p>€150</p>
                </div>
                <p class="lot_nr">
                  <a href="/en/auction/217/lot/240652?sid=1&rn=1">1405</a>
                </p>
                <div class="lot_item lot_240652">
                  <div class="lot_description">Saint Estephe | Mc</div>
                  <div class="lot_name">
                    <a href="/en/auction/217/lot/240652">1920 Chateau Gruaud Larose (by Sarget)</a>
                  </div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]
        details = [item for item in results if isinstance(item, LotDetailItem)]

        self.assertEqual(len(lots), 1)
        self.assertEqual(len(details), 1)
        self.assertEqual(lots[0]["lot_name"], "1920 Chateau Gruaud Larose (by Sarget)")
        self.assertEqual(lots[0]["url"], "https://www.sylvies.be/en/auction/217/lot/240652?sid=1&rn=1")
        self.assertEqual(lots[0]["region"], "Bordeaux")
        self.assertEqual(lots[0]["sub_region"], "Saint Estephe")
        self.assertEqual(lots[0]["country"], "France")
        self.assertEqual(details[0]["lot_producer"], "Chateau Gruaud Larose")
        self.assertEqual(details[0]["vintage"], "1920")
        self.assertEqual(details[0]["unit_format"], "bottle")

    def test_parse_auction_deduplicates_repeated_lot_titles(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation">
              <ul>
                <li class="multiselectbox_title"><label>Wines</label></li>
                <li><label>France (1)</label></li>
                <li class="sub">
                  <label>Bordeaux (1)</label>
                  <ul>
                    <li class="sub_sub"><label>Saint Estephe (1)</label></li>
                  </ul>
                </li>
              </ul>
            </div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>€100 - €200</p>
                  <div class="lot_my_bid"></div><p>€150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/239254?sid=1&rn=2">2</a></p>
                <div class="lot_item lot_239254">
                  <div class="lot_description">Saint Estephe | Mc</div>
                  <div class="lot_name"><a>1929 Chateau Meyney</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
                <div class="lot_item lot_239254">
                  <div class="lot_description">Saint Estephe | Neg</div>
                  <div class="lot_name"><a>1929 Chateau Meyney</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(lots[0]["lot_name"], "1929 Chateau Meyney")

    def test_parse_auction_normalizes_french_accents_in_appellation(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation">
              <ul>
                <li class="multiselectbox_title"><label>Wines</label></li>
                <li><label>France (1)</label></li>
                <li class="sub">
                  <label>Bordeaux (1)</label>
                  <ul>
                    <li class="sub_sub"><label>Haut Médoc (1)</label></li>
                    <li class="sub_sub"><label>Pessac-Léognan (1)</label></li>
                  </ul>
                </li>
              </ul>
            </div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>€100 - €200</p>
                  <div class="lot_my_bid"></div><p>€150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/239255?sid=1&rn=3">3</a></p>
                <div class="lot_item lot_239255">
                  <div class="lot_description">Haut Medoc | Mc</div>
                  <div class="lot_name"><a>1937 Chateau de Camensac</a></div>
                  <div class="lot_bottle">2 Bottle,</div>
                </div>
              </div>
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>€100 - €200</p>
                  <div class="lot_my_bid"></div><p>€150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/239271?sid=1&rn=19">19</a></p>
                <div class="lot_item lot_239271">
                  <div class="lot_description">Pessac Leognan | Neg. Vandermeulen</div>
                  <div class="lot_name"><a>1955 Chateau la Mission Haut Brion</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(lots[0]["region"], "Bordeaux")
        self.assertEqual(lots[0]["sub_region"], "Haut Medoc")
        self.assertEqual(lots[0]["country"], "France")
        self.assertEqual(lots[1]["region"], "Bordeaux")
        self.assertEqual(lots[1]["sub_region"], "Pessac Leognan")
        self.assertEqual(lots[1]["country"], "France")

    def test_parse_auction_handles_empty_link_text_without_dropping_page(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation"><ul></ul></div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>EUR 100 - 200</p>
                  <div class="lot_my_bid"></div><p>EUR 150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/1">1</a></p>
                <div class="lot_item lot_1">
                  <a></a>
                  <div class="lot_name"><a>1990 Chateau Test</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]["external_id"], "sylvies_february-2021_1")

    def test_parse_auction_handles_unknown_volume_without_type_error(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation"><ul></ul></div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>EUR 100 - 200</p>
                  <div class="lot_my_bid"></div><p>EUR 150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/2">2</a></p>
                <div class="lot_item lot_2">
                  <div class="lot_description">Bordeaux | Mc</div>
                  <div class="lot_name"><a>1991 Chateau Test</a></div>
                  <div class="lot_bottle">1 x mystery-format,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(len(lots), 1)
        self.assertIsNone(lots[0]["volume"])

    def test_parse_auction_uses_lot_href_when_lot_class_id_is_missing(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation"><ul></ul></div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>EUR 100 - 200</p>
                  <div class="lot_my_bid"></div><p>EUR 150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/241/lot/123456?sid=1&rn=1">1</a></p>
                <div class="lot_item">
                  <div class="lot_description">Bordeaux | Mc</div>
                  <div class="lot_name"><a>1992 Chateau From Href</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]["external_id"], "sylvies_february-2021_123456")

    def test_parse_auction_skips_lot_without_source_id_but_keeps_later_lots(self):
        spider = SylviesSpider.__new__(SylviesSpider)
        html = """
        <html>
          <body>
            <div class="multiselectbox_select select_appelation"><ul></ul></div>
            <div class="auction_lots">
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>EUR 100 - 200</p>
                  <div class="lot_my_bid"></div><p>EUR 150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/missing">missing</a></p>
                <div class="lot_item">
                  <div class="lot_name"><a>1992 Missing Id</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
              <div class="auction_item">
                <div class="large-2 columns auction_infos">
                  <div class="lot_estimate"></div><p>EUR 100 - 200</p>
                  <div class="lot_my_bid"></div><p>EUR 150</p>
                </div>
                <p class="lot_nr"><a href="/en/auction/217/lot/3">3</a></p>
                <div class="lot_item lot_3">
                  <div class="lot_name"><a>1993 Chateau Good</a></div>
                  <div class="lot_bottle">1 Bottle,</div>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        results = list(spider.parse_auction(self.make_response(html)))
        lots = [item for item in results if isinstance(item, LotItem)]

        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]["external_id"], "sylvies_february-2021_3")

    def test_failed_paginated_page_recovers_by_scheduling_next_page(self):
        class Failure:
            request = Request(
                "https://www.sylvies.be/en/auction/183?sort=lotnr_asc&page=59",
                meta={
                    "auction_id": "sylvies_december-2016",
                    "auction_item": None,
                    "pagination_failures": 0,
                },
            )

            def getErrorMessage(self):
                return "ConnectionLost"

        spider = SylviesSpider.__new__(SylviesSpider)

        results = list(spider.parse_auction_error(Failure()))

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].url,
            "https://www.sylvies.be/en/auction/183?sort=lotnr_asc&page=60",
        )
        self.assertEqual(results[0].meta["pagination_failures"], 1)

    def test_failed_paginated_page_stops_after_three_consecutive_failures(self):
        class Failure:
            request = Request(
                "https://www.sylvies.be/en/auction/183?sort=lotnr_asc&page=59",
                meta={
                    "auction_id": "sylvies_december-2016",
                    "auction_item": None,
                    "pagination_failures": 2,
                },
            )

            def getErrorMessage(self):
                return "ConnectionLost"

        spider = SylviesSpider.__new__(SylviesSpider)

        self.assertEqual(list(spider.parse_auction_error(Failure())), [])


class TestSylviesPdfDateParsing(unittest.TestCase):
    def test_parse_pdf_text_uses_full_dates_from_old_catalog_format(self):
        text = (
            "\x001\x006\x00/\x000\x003\x00/\x002\x000\x001\x002 "
            "\x00A\x00u\x00c\x00t\x00i\x00o\x00n \x00 \x00c\x00a\x00t\x00a\x00l\x00o\x00g\x00u\x00e\x00: "
            "\x00a\x00t \x001\x004\x00:\x000\x000 \x00h\x00r\x00s "
            "\x00& \x001\x007\x00/\x000\x003\x00/\x002\x000\x001\x002 "
            "\x00a\x00t \x001\x000\x00:\x000\x000 \x00h\x00r\x00s"
        )

        result = parse_pdf_dates_from_text(text)

        self.assertEqual(result["start_date"], "2012-03-16")
        self.assertEqual(result["end_date"], "2012-03-17")

    def test_parse_pdf_text_uses_auction_year_for_short_catalog_dates(self):
        text = "Auction catalogue: 02/12 at 10:00 CET from lot 1 04/12 at 10:00 CET"

        result = parse_pdf_dates_from_text(text, default_year=2021)

        self.assertEqual(result["start_date"], "2021-12-02")
        self.assertEqual(result["end_date"], "2021-12-04")


if __name__ == "__main__":
    unittest.main()
