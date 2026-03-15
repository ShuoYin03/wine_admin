from wine_spider.wine_spider.services import auction_sales_client, auctions_client, lots_client, lot_items_client
from wine_spider.wine_spider.items import AuctionSalesItem

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

            initial_data = {
                "lots": 0,
                "sold": 0,
                "total_low_estimate": 0,
                "total_high_estimate": 0,
                "total_sales": 0,
                "volume_sold": 0,
                "top_lot": None,
                "top_lot_price": 0,
                "single_cellar_check": None,
                "single_cellar": True,
                "currency": None
            }

            for lot in lots:
                if lot.get('original_currency') and initial_data['currency'] is None:
                    initial_data['currency'] = lot.get('original_currency')
                initial_data['lots'] += 1
                initial_data['total_low_estimate'] += lot.get('low_estimate') if 'low_estimate' in lot and lot['low_estimate'] else 0
                initial_data['total_high_estimate'] += lot.get('high_estimate') if 'high_estimate' in lot and lot['high_estimate'] else 0
                if lot['sold']:
                    initial_data['sold'] += 1
                    initial_data['total_sales'] += lot['end_price'] if lot['end_price'] else 0
                    initial_data['volume_sold'] += lot['volume'] if 'volume' in lot and lot['volume'] else 0
                    if lot['end_price'] > initial_data['top_lot_price']:
                        initial_data['top_lot_price'] = lot['end_price']
                        initial_data['top_lot'] = lot['external_id']
            
            for lot_item in lot_items:
                producer = lot_item.get('lot_producer', None)
                if producer is None:
                    continue
                if initial_data['single_cellar_check'] is None:
                    initial_data['single_cellar_check'] = producer
                elif initial_data['single_cellar_check'] != producer:
                    initial_data['single_cellar'] = False

            auction_sales_item = AuctionSalesItem(
                auction_id=auction_id,
                lots=initial_data['lots'],
                sold=initial_data['sold'],
                currency=initial_data['currency'],
                total_low_estimate=initial_data['total_low_estimate'],
                total_high_estimate=initial_data['total_high_estimate'],
                total_sales=initial_data['total_sales'],
                volume_sold=initial_data['volume_sold'],
                top_lot=initial_data['top_lot'],
                single_cellar=initial_data['single_cellar'],
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
