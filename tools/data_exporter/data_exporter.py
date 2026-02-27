import csv
import argparse
from datetime import datetime
from shared.database.data_export_client import DataExportClient
from dotenv import load_dotenv

load_dotenv()

lots_export_client = DataExportClient()

def _parse_date(value: str):
    if not value:
        return None
    return datetime.fromisoformat(value)

def lot_export_to_csv(auction_house: str, output_path: str, start_date=None, end_date=None):
    client = DataExportClient()
    data = client.export_lots_with_items_by_house(auction_house, start_date=start_date, end_date=end_date)

    if not data:
        print("No data found.")
        return

    fieldnames = [
        "id", "name", "lwin_7", "lwin_11", "type", "volume", "unit", "original_currency",
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

def auction_export_to_csv(auction_house: str, output_path: str, start_date=None, end_date=None):
    client = DataExportClient()
    data = client.export_auctions_by_house(auction_house, start_date=start_date, end_date=end_date)

    if not data:
        print("No data found.")
        return
        
    fieldnames = [
        "id", "title", "house", "city", "continent", "start_date",
        "end_date", "year", "quarter", "lots", "sold", "currency",
        "total_low_estimate", "total_high_estimate", "total_sales",
        "volume_sold", "top_lot", "single_cellar", "url"
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Export completed. CSV saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export data by auction house")
    parser.add_argument("--auction_house", required=True, help="Auction house name (e.g. Sothebys)")
    parser.add_argument("--type", required=True, help="Type of data to export (e.g. lots, auctions)")
    parser.add_argument("--start-date", help="Filter auctions with start_date >= this ISO date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
    parser.add_argument("--end-date", help="Filter auctions with end_date <= this ISO date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")

    args = parser.parse_args()

    start_date = _parse_date(args.start_date)
    end_date = _parse_date(args.end_date) if args.end_date else datetime.now()

    if args.auction_house == "all":
        auction_houses = [
            "Sotheby's", 
            "Christie's", 
            "Bonhams",
            "Sylvie's",
            "Wineauctioneer",
            "Baghera",
            "Tajan",
            "Zachys",
            "Steinfels"            
        ]
        for house in auction_houses:
            if args.type == "lots":
                lot_export_to_csv(house, f"{house}_lots.csv", start_date=start_date, end_date=end_date)
            elif args.type == "auctions":
                auction_export_to_csv(house, f"{house}_auctions.csv", start_date=start_date, end_date=end_date)
    else:
        if args.type == "lots":
            lot_export_to_csv(args.auction_house, f"{args.auction_house}_lots.csv", start_date=start_date, end_date=end_date)
        elif args.type == "auctions":
            auction_export_to_csv(args.auction_house, f"{args.auction_house}_auctions.csv", start_date=start_date, end_date=end_date)