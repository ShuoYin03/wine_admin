import asyncio
import aiohttp
from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

async def main():
    api_url = "https://auktionen.steinfelsweine.ch/api/auctions?archived=true"

    headers = {
        "x-api-version": "1.15"
    }
    
    report = AuctionScrapingReportGenerator("Steinfels")

    auction_lots_data = report.load_lot_counts_from_db()
    print(auction_lots_data)

    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(api_url, headers=headers) as response:
            if response.status != 200:
                print(f"Failed to fetch auction data: {response.status}")
                return
            
            items = await response.json()
            for item in items: 
                external_id = f"steinfels_{item.get('id')}"
                hits = item.get("catalogs", {})[0].get("parts", {})[0].get("lotNumberEnd")

                for auction in auction_lots_data:
                    if auction['external_id'] == external_id:
                        url = auction['url']
                        lot_count = auction['lot_count']
                        match = hits == auction['lot_count']
                        report.add_result(
                            external_id=external_id, 
                            hits=hits, 
                            lot_count=lot_count, 
                            match=match, 
                            url=url
                        )
                        break

    report.export()

if __name__ == "__main__":
    asyncio.run(main())