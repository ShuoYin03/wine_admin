import csv
from sqlalchemy import func, desc
from database.model import AuctionModel, LotModel
from database import AuctionsClient

class AuctionScrapingReportGenerator:
    def __init__(self, auction_house: str):
        self.auction_house = auction_house
        self.total_actual_count = 0
        self.total_expected_count = 0
        self.false_count = 0
        self.detailed_rows = []
        self.report_file = f"{auction_house}_scraping_report.csv"

    def add_result(self, external_id, hits, lot_count, match, url):
        self.total_expected_count += hits
        self.total_actual_count += lot_count
        if not match:
            self.false_count += 1

        self.detailed_rows.append({
            "external_id": external_id,
            "hits": hits,
            "lot_count": lot_count,
            "match": match,
            "url": url
        })

    def load_lot_counts_from_db(self):
        client = AuctionsClient()

        with client.session_scope() as session:
            query = (
                session.query(
                    AuctionModel.external_id,
                    AuctionModel.url,
                    func.count(LotModel.id).label("lot_count")
                )
                .outerjoin(LotModel, AuctionModel.external_id == LotModel.auction_id)
                .filter(AuctionModel.auction_house == self.auction_house)
                .group_by(AuctionModel.external_id, AuctionModel.url)
                .order_by(desc("lot_count"))
            )

            results = query.all()

        return [
            {
                "external_id": row.external_id,
                "url": row.url,
                "lot_count": row.lot_count
            }
            for row in results
        ]

    def export(self):
        sorted_rows = sorted(self.detailed_rows, key=lambda r: r["match"])

        with open(self.report_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            writer.writerow(["Auction House", self.auction_house])
            writer.writerow(["Total Auctions Scraped", len(self.detailed_rows)])
            writer.writerow(["Total Expected Lot Count", self.total_expected_count])
            writer.writerow(["Total Scraped Lot Count", self.total_actual_count])
            writer.writerow(["Matched Auctions", len(self.detailed_rows) - self.false_count])
            writer.writerow(["Mismatched Auctions", self.false_count])
            writer.writerow(["Auction Matching Accuracy (%)", 
                             round(100 * (1 - self.false_count / len(self.detailed_rows)), 2) if self.detailed_rows else 100])
            writer.writerow(["Lot Matching Accuracy (%)", 
                             round(100 * (self.total_actual_count / self.total_expected_count), 2) if self.total_expected_count else 100])

            writer.writerow([])

            writer.writerow(["external_id", "hits_from_api", "lot_count_in_db", "match_status", "auction_url"])
            for row in sorted_rows:
                writer.writerow([
                    row["external_id"],
                    row["hits"],
                    row["lot_count"],
                    "✅" if row["match"] else "❌",
                    row["url"]
                ])

        print(f"Report generated: {self.report_file}")
