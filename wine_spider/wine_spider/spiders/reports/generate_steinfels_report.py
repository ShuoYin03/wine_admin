import asyncio
import aiohttp
from wine_spider.services.steinfels_client import SteinfelsClient
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

HEADERS = {
    "x-api-version": "1.15"
}


def extract_expected_lot_count(lot_response: dict, auction: dict) -> int:
    total_count = lot_response.get("$totalCount")
    if isinstance(total_count, int):
        return total_count

    catalogs = auction.get("catalogs") or []
    if not catalogs:
        return 0

    parts = catalogs[0].get("parts") or []
    lot_number_ends = [
        part.get("lotNumberEnd")
        for part in parts
        if isinstance(part.get("lotNumberEnd"), int)
    ]
    return max(lot_number_ends, default=0)


async def fetch_expected_lot_count(session, sem, client, auction):
    catalogs = auction.get("catalogs") or []
    catalog = catalogs[0] if catalogs else {}
    catalog_id = catalog.get("id")
    external_id = f"steinfels_{auction.get('id')}"

    if catalog_id is None:
        return external_id, 0

    async with sem:
        async with session.get(
            client.get_lot_api_url(catalog_id, page=1),
            headers=HEADERS,
        ) as response:
            if response.status != 200:
                print(f"Failed to fetch Steinfels lots for {external_id}: {response.status}")
                return external_id, extract_expected_lot_count({}, auction)

            lot_response = await response.json()
            return external_id, extract_expected_lot_count(lot_response, auction)

async def main():
    api_url = "https://auktionen.steinfelsweine.ch/api/auctions?archived=true"
    client = SteinfelsClient()
    
    report = AuctionScrapingReportGenerator("Steinfels")

    auction_lots_data = report.load_lot_counts_from_db()
    auction_lots_by_id = {
        row["external_id"]: row
        for row in auction_lots_data
    }

    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(api_url, headers=HEADERS) as response:
            if response.status != 200:
                print(f"Failed to fetch auction data: {response.status}")
                return
            
            items = await response.json()
            sem = asyncio.Semaphore(SEM_LIMIT)
            results = await asyncio.gather(
                *[
                    fetch_expected_lot_count(session, sem, client, item)
                    for item in items
                ]
            )

            for external_id, hits in results:
                auction = auction_lots_by_id.get(external_id)
                if auction:
                    lot_count = auction["lot_count"]
                    url = auction["url"]
                else:
                    lot_count = 0
                    url = ""

                report.add_result(
                    external_id=external_id,
                    hits=hits,
                    lot_count=lot_count,
                    match=hits == lot_count,
                    url=url,
                )

    report.export()

if __name__ == "__main__":
    asyncio.run(main())
