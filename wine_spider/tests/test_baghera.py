from __future__ import annotations

import re
import unittest
import requests
from tests.utils import live_html
from wine_spider.items import LotItem
from wine_spider.helpers import unit_format_to_volume
from wine_spider.exceptions import NoPreDefinedVolumeIdentifierException

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


if __name__ == "__main__":
    unittest.main()
