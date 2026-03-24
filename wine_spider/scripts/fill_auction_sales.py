from wine_spider.wine_spider.services import auction_sales_client, auctions_client, lots_client, lot_items_client
from wine_spider.wine_spider.items import AuctionSalesItem
from wine_spider.wine_spider.helpers.auction_aggregator import compute_auction_sales_stats


class AuctionSalesFiller:
    def __init__(self, auction_house: str):
        self.auction_house = auction_house
        self.auction_sales_client = auction_sales_client
        self.auctions_client = auctions_client
        self.lots_client = lots_client
        self.lot_items_client = lot_items_client

    def fill_auction_sales(self, overwrite: bool = False):
        print("Filling auction sales...")

        auctions = self.auctions_client.get_all_by_auction_house(self.auction_house)
        filled_auction_sales = 0
        for auction in auctions:
            auction_id = auction['external_id']
            auction_sales = self.auction_sales_client.get_by_external_id(auction_id)
            if auction_sales and not overwrite:
                print(f"Auction sales for auction {auction_id} already exist. Skipping...")
                continue
            lots = self.lots_client.get_all_by_auction(auction_id)
            lot_items = self.lot_items_client.get_all_by_auction(auction_id)
            if not lots:
                print(f"No lots found for auction {auction_id}. Skipping...")
                continue

            stats = compute_auction_sales_stats(lots, lot_items)

            auction_sales_item = AuctionSalesItem(
                auction_id=auction_id,
                lots=stats['lots'],
                sold=stats['sold'],
                currency=stats['currency'],
                total_low_estimate=stats['total_low_estimate'],
                total_high_estimate=stats['total_high_estimate'],
                total_sales=stats['total_sales'],
                volume_sold=stats['volume_sold'],
                top_lot=stats['top_lot'],
                single_cellar=stats['single_cellar'],
                ex_ch=False
            )

            self.auction_sales_client.upsert_by_external_id(auction_sales_item)
            filled_auction_sales += 1
            print(f"Filled auction sales for auction {auction_id}")

        print(f"Filled {filled_auction_sales} auction sales for {self.auction_house}.")
        print("Auction sales filling completed.")


if __name__ == "__main__":
    auction_house = "Sotheby's"
    filler = AuctionSalesFiller(auction_house)
    filler.fill_auction_sales(overwrite=True)
