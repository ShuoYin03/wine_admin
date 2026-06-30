import asyncio
import aiohttp
from wine_spider.services.bonhams_client import BonhamsClient
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10


def get_bonhams_report_api_config():
    client = BonhamsClient()
    return client.api_url, client.headers

async def fetch_hits(session, url, payload, headers):
    results = []
    async with session.post(url, json=payload, headers=headers) as response:
        if response.status != 200:
            print(f"Failed to fetch auction page: {response.status}")
            return
            
        data = await response.json()
        documents = data['results'][0]['hits']
        for document in documents:
            document = document.get("document")
            hits = document['lots']['total']
            external_id = document['id']
            results.append((hits, external_id))

    return results

async def main():
    client = BonhamsClient()
    bonhams_api_url, headers = get_bonhams_report_api_config()

    report = AuctionScrapingReportGenerator("Bonhams")

    auction_lots_data = report.load_lot_counts_from_db()
    auction_lots_by_id = {
        row["external_id"]: row
        for row in auction_lots_data
    }

    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for page in range(1, 5):
            payload = client.get_auction_search_payload(page=page)
            tasks.append(fetch_hits(session, bonhams_api_url, payload, headers))

        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                for hits, external_id in result:
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
