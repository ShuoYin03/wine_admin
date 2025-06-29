import asyncio
import aiohttp
from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

def get_bonhams_payload(page=1, per_page=250):
    return {
        "searches": [
            {
                "collection": "auctions-search",
                "exclude_fields": "description",
                "filter_by": "(biddingStatus:=EN) && (brand:=[`bonhams`, `skinner`, `cornette`, `bonhams-cars`]) && (categories.name:=[`Wine & Whisky`]) && (auctionType:=[`ONLINE`, `PUBLIC`])",
                "facet_by": "",
                "query_by": "auctionHeading,auctionTitle,departments.name",
                "sort_by": "hammerTime.timestamp:desc,auctionTitle:desc",
                "page": page,
                "per_page": per_page,
                "max_facet_values": 300,
                "q": ""
            }
        ]
    }

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
    bonhams_api_url = "https://api01.bonhams.com/search/multi_search?use_cache=true&enable_lazy_filter=true"
    headers = {
        "x-typesense-api-key": "d5tG3PtISgJs8rpfw1H2mJ7kq5ONSEhX"
    }

    report = AuctionScrapingReportGenerator("Bonhams")

    auction_lots_data = report.load_lot_counts_from_db()

    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            fetch_hits(session, bonhams_api_url, get_bonhams_payload(page), headers) 
            for page in range(0, 4)
        ]

        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                for hits, external_id in result:
                    for auction in auction_lots_data:
                        if auction['external_id'] == external_id:
                            lot_count = auction['lot_count']
                            url = auction['url']
                            match = hits == lot_count
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