import asyncio
from dotenv import load_dotenv
from database import LotsClient, AuctionsClient

load_dotenv()

class DatabaseQueryTest:
    def __init__(self):
        self.lots_client = LotsClient()
        self.auctions_client = AuctionsClient()

    async def test_insert_lot(self):
        payload = {
            "id": 1,
            "external_id": "LOT-EXTERNAL-001",
            "auction_id": "AUC-EXTERNAL-001",
            "lot_name": "Château Lafite Rothschild 2010",
            "lot_type": ["Wine"],
            "volume": 750.0,
            "unit": 6,
            "original_currency": "USD",
            "start_price": 1000,
            "end_price": 1500,
            "low_estimate": 900,
            "high_estimate": 1600,
            "sold": True,
            "sold_date": "2024-05-01",
            "region": "Bordeaux",
            "sub_region": "Pauillac",
            "country": "France",
            "success": True,
            "url": "https://example.com/lots/lot-external-001"
        }
        
        self.lots_client.upsert_lot(payload)
    
    async def test_insert_auction(self):
        payload = {
            "id": 1,
            "external_id": "AUC-EXTERNAL-001",
            "auction_title": "Fine & Rare Wines Auction - Spring 2025",
            "auction_house": "Sotheby's",
            "city": "London",
            "continent": "Europe",
            "start_date": "2025-05-15",
            "end_date": "2025-05-17",
            "year": 2025,
            "quarter": 2,
            "auction_type": "Fine Wine",
            "url": "https://example.com/auctions/auc-external-001"
        }
        
        self.auctions_client.upsert(payload)

    async def test_query_lots_with_auction(self):
        # filters = {
        #     "auction_id": "AUC-EXTERNAL-001",
        #     "sold": True
        # }
        # order_by = ["end_price"]
        # limit = 10
        # offset = 0
        
        data, count = self.lots_client.query_lots_with_auction(
            # filters=filters,
            # order_by=order_by,
            # limit=limit,
            # offset=offset,
            return_count=True
        )
        
        print(f"Count: {count}")
        for row in data:
            print(row)

if __name__ == '__main__':
    test = DatabaseQueryTest()
    asyncio.run(test.test_query_lots_with_auction())
