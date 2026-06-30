import asyncio
import aiohttp
from wine_spider.services import SothebysClient
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10
REPORT_FILE = "sothebys_report.csv"


GRAPHQL_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.sothebys.com",
    "Referer": "https://www.sothebys.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
}


def extract_algolia_key(payload: dict) -> str | None:
    return (
        (payload.get("data") or {})
        .get("algoliaSearchKey", {})
        .get("key")
    )


async def fetch_hits(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                     client: SothebysClient, external_id: str, url: str, lot_count: int):
    async with sem:
        async with session.post(
            client.api_url,
            headers=GRAPHQL_HEADERS,
            json=client.algolia_search_key_query(external_id),
        ) as key_resp:
            key_data = await key_resp.json()

        api_key = extract_algolia_key(key_data)
        if not api_key and url:
            async with session.get(url) as resp:
                html = await resp.text()
            api_key = client.extract_algolia_api_key(html)

        if not api_key:
            return {
                "external_id": external_id,
                "hits": 0,
                "lot_count": lot_count,
                "match": lot_count == 0,
                "error": f"missing_algolia_key: {key_data}",
            }

        api_url, headers, payload = client.algolia_api(
            auction_id=external_id,
            api_key=api_key,
            page=1
        )

        async with session.post(api_url, headers=headers, json=payload) as resp2:
            data = await resp2.json()
            hits = data.get("nbHits") or data.get("facets", {}) \
                    .get("lotState", {}) \
                    .get("Closed", 0)

    return {
        "external_id": external_id,
        "hits": hits,
        "lot_count": lot_count,
        "match": hits == lot_count,
        "error": None,
    }

async def main():
    report = AuctionScrapingReportGenerator("Sotheby's")

    auction_lots_data = report.load_lot_counts_from_db()

    sem = asyncio.Semaphore(SEM_LIMIT)
    client = SothebysClient()
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            fetch_hits(session, sem, client, row["external_id"], row["url"], row["lot_count"])
            for row in auction_lots_data
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, r in enumerate(results):
        if isinstance(r, Exception):
            continue
        report.add_result(
            external_id=r["external_id"],
            hits=r["hits"],
            lot_count=r["lot_count"],
            match=r["match"],
            url=auction_lots_data[i]["url"]
        )

    report.export()

if __name__ == "__main__":
    asyncio.run(main())
