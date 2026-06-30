import argparse

from wine_spider.services.database import auction_sales_client, auctions_client, lots_client, lot_items_client
from wine_spider.helpers.auction_aggregator import compute_auction_sales_stats


AUCTION_HOUSES = [
    "Sotheby's",
    "Christie's",
    "Bonhams",
    "Sylvie's",
    "Wineauctioneer",
    "Baghera",
    "Tajan",
    "Zachys",
    "Steinfels",
]


class AuctionSalesFiller:
    def __init__(self, auction_house: str):
        self.auction_house = auction_house
        self.auction_sales_client = auction_sales_client
        self.auctions_client = auctions_client
        self.lots_client = lots_client
        self.lot_items_client = lot_items_client

    def _build_auction_sales_item(self, auction: dict, stats: dict) -> dict:
        return {
            "auction_id": auction["external_id"],
            "lots": stats["lots"],
            "sold": stats["sold"],
            "currency": stats["currency"],
            "total_low_estimate": stats["total_low_estimate"],
            "total_high_estimate": stats["total_high_estimate"],
            "total_sales": stats["total_sales"],
            "volume_sold": stats["volume_sold"],
            "top_lot": stats["top_lot"],
            "sale_type": auction.get("auction_type") or "PAST",
            "single_cellar": stats["single_cellar"],
            "ex_ch": False,
        }

    def _empty_auction_sales_stats(self) -> dict:
        return {
            "lots": 0,
            "sold": 0,
            "currency": None,
            "total_low_estimate": 0,
            "total_high_estimate": 0,
            "total_sales": 0,
            "volume_sold": 0,
            "top_lot": None,
            "single_cellar": True,
        }

    def _auction_sales_lot_count(self, auction_sales):
        if isinstance(auction_sales, dict):
            return auction_sales.get("lots")
        return getattr(auction_sales, "lots", None)

    def _is_zero_lot_summary(self, auction_sales) -> bool:
        lot_count = self._auction_sales_lot_count(auction_sales)
        try:
            return int(lot_count) == 0
        except (TypeError, ValueError):
            return False

    def fill_auction_sales(self, overwrite: bool = False, fill_empty_auctions: bool = False):
        print("Filling auction sales...")

        auctions = self.auctions_client.get_all_by_auction_house(
            self.auction_house,
            lambda auction: auction.model_to_dict(),
        )
        filled_auction_sales = 0
        for auction in auctions:
            auction_id = auction['external_id']
            auction_sales = self.auction_sales_client.get_by_external_id(auction_id)
            if (
                auction_sales
                and not overwrite
                and not self._is_zero_lot_summary(auction_sales)
            ):
                print(f"Auction sales for auction {auction_id} already exist. Skipping...")
                continue
            lots = self.lots_client.get_all_by_auction(auction_id)
            if not lots:
                if not fill_empty_auctions:
                    print(f"No lots found for auction {auction_id}. Skipping...")
                    continue
                stats = self._empty_auction_sales_stats()
            else:
                lot_items = self.lot_items_client.get_all_by_auction(auction_id)
                stats = compute_auction_sales_stats(lots, lot_items)

            auction_sales_item = self._build_auction_sales_item(auction, stats)

            self.auction_sales_client.upsert_by_external_id(auction_sales_item)
            filled_auction_sales += 1
            print(f"Filled auction sales for auction {auction_id}")

        print(f"Filled {filled_auction_sales} auction sales for {self.auction_house}.")
        print("Auction sales filling completed.")
        return filled_auction_sales


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill auction_sales from stored lots and lot_items.")
    parser.add_argument("--auction-house", default="all", help="Auction house name or 'all'")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing auction_sales rows")
    parser.add_argument(
        "--fill-empty-auctions",
        action="store_true",
        help="Create zero-value auction_sales rows for auctions with no stored lots",
    )
    args = parser.parse_args()

    houses = AUCTION_HOUSES if args.auction_house == "all" else [args.auction_house]
    total = 0
    for auction_house in houses:
        filler = AuctionSalesFiller(auction_house)
        total += filler.fill_auction_sales(
            overwrite=args.overwrite,
            fill_empty_auctions=args.fill_empty_auctions,
        )
    print(f"Filled {total} auction sales rows in total.")
