import csv
import argparse
from database import LotsExportClient

lots_export_client = LotsExportClient()

def export_to_csv(auction_house: str, output_path: str):
    client = LotsExportClient()
    data = client.export_lots_with_items_by_house(auction_house)

    if not data:
        print("No data found.")
        return

    fieldnames = [
        "id", "name", "type", "volume", "unit", "original_currency",
        "start_price", "end_price", "low_estimate", "high_estimate", "sold",
        "sold_date", "region", "sub_region", "country", "url",
        "item_producer", "item_vintage", "item_unit_format", "item_wine_colour",
        "auction_title", "auction_house", "auction_city", "auction_continent",
        "auction_start_date", "auction_end_date", "auction_year", "auction_quarter", "auction_url"
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Export completed. CSV saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export lots data by auction house")
    parser.add_argument("--auction_house", required=True, help="Auction house name (e.g. Sothebys)")

    args = parser.parse_args()

    export_to_csv(args.auction_house, f"{args.auction_house}_lots.csv")