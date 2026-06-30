from __future__ import annotations

import unittest
from unittest.mock import Mock

from scripts.fill_auction_sales import AuctionSalesFiller


class AuctionSalesFillerTests(unittest.TestCase):
    def test_fill_auction_sales_uses_current_client_contract_and_upserts_dict(self):
        filler = AuctionSalesFiller("Test House")
        filler.auctions_client = Mock()
        filler.auction_sales_client = Mock()
        filler.lots_client = Mock()
        filler.lot_items_client = Mock()

        filler.auctions_client.get_all_by_auction_house.return_value = [
            {"external_id": "auction-1", "auction_type": "PAST"}
        ]
        filler.auction_sales_client.get_by_external_id.return_value = None
        filler.lots_client.get_all_by_auction.return_value = [
            {
                "external_id": "lot-1",
                "original_currency": "USD",
                "low_estimate": 100,
                "high_estimate": 200,
                "sold": True,
                "end_price": 150,
                "volume": 1.5,
            }
        ]
        filler.lot_items_client.get_all_by_auction.return_value = [
            {"lot_producer": "Producer A"}
        ]

        filled = filler.fill_auction_sales(overwrite=False)

        self.assertEqual(filled, 1)
        self.assertTrue(filler.auctions_client.get_all_by_auction_house.call_args.args[1])
        saved = filler.auction_sales_client.upsert_by_external_id.call_args.args[0]
        self.assertEqual(saved["auction_id"], "auction-1")
        self.assertEqual(saved["lots"], 1)
        self.assertEqual(saved["sold"], 1)
        self.assertEqual(saved["total_sales"], 150)
        self.assertEqual(saved["sale_type"], "PAST")

    def test_fill_auction_sales_skips_existing_rows_without_overwrite(self):
        filler = AuctionSalesFiller("Test House")
        filler.auctions_client = Mock()
        filler.auction_sales_client = Mock()
        filler.lots_client = Mock()
        filler.lot_items_client = Mock()

        filler.auctions_client.get_all_by_auction_house.return_value = [
            {"external_id": "auction-1", "auction_type": "PAST"}
        ]
        filler.auction_sales_client.get_by_external_id.return_value = {"auction_id": "auction-1"}

        filled = filler.fill_auction_sales(overwrite=False)

        self.assertEqual(filled, 0)
        filler.lots_client.get_all_by_auction.assert_not_called()
        filler.auction_sales_client.upsert_by_external_id.assert_not_called()

    def test_fill_auction_sales_repairs_existing_zero_lot_summary(self):
        filler = AuctionSalesFiller("Test House")
        filler.auctions_client = Mock()
        filler.auction_sales_client = Mock()
        filler.lots_client = Mock()
        filler.lot_items_client = Mock()

        filler.auctions_client.get_all_by_auction_house.return_value = [
            {"external_id": "auction-1", "auction_type": "PAST"}
        ]
        filler.auction_sales_client.get_by_external_id.return_value = {
            "auction_id": "auction-1",
            "lots": 0,
        }
        filler.lots_client.get_all_by_auction.return_value = [
            {
                "external_id": "lot-1",
                "original_currency": "HKD",
                "low_estimate": 1000,
                "high_estimate": 2000,
                "sold": True,
                "end_price": 2500,
                "volume": 750,
            },
            {
                "external_id": "lot-2",
                "original_currency": "HKD",
                "low_estimate": 2000,
                "high_estimate": 3000,
                "sold": False,
                "end_price": None,
                "volume": 750,
            },
        ]
        filler.lot_items_client.get_all_by_auction.return_value = [
            {"lot_producer": "Producer A"},
            {"lot_producer": "Producer A"},
        ]

        filled = filler.fill_auction_sales(overwrite=False)

        self.assertEqual(filled, 1)
        saved = filler.auction_sales_client.upsert_by_external_id.call_args.args[0]
        self.assertEqual(saved["auction_id"], "auction-1")
        self.assertEqual(saved["lots"], 2)
        self.assertEqual(saved["sold"], 1)
        self.assertEqual(saved["currency"], "HKD")
        self.assertEqual(saved["total_sales"], 2500)

    def test_fill_auction_sales_can_create_zero_stats_for_empty_auctions(self):
        filler = AuctionSalesFiller("Test House")
        filler.auctions_client = Mock()
        filler.auction_sales_client = Mock()
        filler.lots_client = Mock()
        filler.lot_items_client = Mock()

        filler.auctions_client.get_all_by_auction_house.return_value = [
            {"external_id": "auction-1", "auction_type": None}
        ]
        filler.auction_sales_client.get_by_external_id.return_value = None
        filler.lots_client.get_all_by_auction.return_value = []
        filler.lot_items_client.get_all_by_auction.return_value = []

        filled = filler.fill_auction_sales(
            overwrite=False,
            fill_empty_auctions=True,
        )

        self.assertEqual(filled, 1)
        saved = filler.auction_sales_client.upsert_by_external_id.call_args.args[0]
        self.assertEqual(saved["auction_id"], "auction-1")
        self.assertEqual(saved["lots"], 0)
        self.assertEqual(saved["sold"], 0)
        self.assertIsNone(saved["currency"])
        self.assertEqual(saved["total_low_estimate"], 0)
        self.assertEqual(saved["total_high_estimate"], 0)
        self.assertEqual(saved["total_sales"], 0)
        self.assertEqual(saved["volume_sold"], 0)
        self.assertIsNone(saved["top_lot"])
        self.assertEqual(saved["sale_type"], "PAST")
        self.assertTrue(saved["single_cellar"])
        self.assertFalse(saved["ex_ch"])


if __name__ == "__main__":
    unittest.main()
