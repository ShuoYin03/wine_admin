import csv
from .model import AuctionModel, LotModel, LotItemModel
from .base_database_client import BaseDatabaseClient

class LotsExportClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotModel, db_instance=db_instance)

    def export_lots_with_items_by_house(self, auction_house: str):
        with self.session_scope() as session:
            query = (
                session.query(LotModel, LotItemModel, AuctionModel)
                .join(AuctionModel, LotModel.auction_id == AuctionModel.external_id)
                .join(LotItemModel, LotModel.external_id == LotItemModel.lot_id)
                .filter(AuctionModel.auction_house == auction_house)
            )

            rows = query.all()

            data = []
            for lot, lot_item, auction in rows:
                data.append({
                    "id": lot.id,
                    "name": lot.lot_name,
                    "type": lot.lot_type,
                    "volume": lot.volume,
                    "unit": lot.unit,
                    "original_currency": lot.original_currency,
                    "start_price": lot.start_price,
                    "end_price": lot.end_price,
                    "low_estimate": lot.low_estimate,
                    "high_estimate": lot.high_estimate,
                    "sold": lot.sold,
                    "sold_date": lot.sold_date,
                    "region": lot.region,
                    "sub_region": lot.sub_region,
                    "country": lot.country,
                    "url": lot.url,
                    "item_producer": lot_item.lot_producer,
                    "item_vintage": lot_item.vintage,
                    "item_unit_format": lot_item.unit_format,
                    "item_wine_colour": lot_item.wine_colour,
                    "auction_title": auction.auction_title,
                    "auction_house": auction.auction_house,
                    "auction_city": auction.city,
                    "auction_continent": auction.continent,
                    "auction_start_date": auction.start_date,
                    "auction_end_date": auction.end_date,
                    "auction_year": auction.year,
                    "auction_quarter": auction.quarter,
                    "auction_url": auction.url
                })

            return data

def export_to_csv(auction_house: str, output_path: str):
    client = LotsExportClient()
    data = client.export_lots_with_items_by_house(auction_house)

    if not data:
        print("No data found.")
        return

    with open(output_path, "w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Export completed. CSV saved to {output_path}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Export lots data by auction house")
    parser.add_argument("--auction_house", required=True, help="Auction house name (e.g. Sothebys)")
    parser.add_argument("--output", default="lots_export.csv", help="Output CSV file path")

    args = parser.parse_args()

    export_to_csv(args.auction_house, args.output)