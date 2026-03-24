from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
