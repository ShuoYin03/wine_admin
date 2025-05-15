import asyncio
import csv
import pandas as pd
import aiohttp
from wine_spider.wine_spider.services import SothebysClient

SEM_LIMIT = 10
REPORT_FILE = "auction_report.csv"

async def fetch_hits(session: aiohttp.ClientSession, sem: asyncio.Semaphore,
                     client: SothebysClient, external_id: str, url: str, lot_count: int):
    async with sem:
        async with session.get(url) as resp:
            html = await resp.text()

        api_key = client.extract_algolia_api_key(html)
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
        "match": hits == lot_count
    }

async def main():
    df = pd.read_csv("auction-lots-number.csv")
    client = SothebysClient()

    sem = asyncio.Semaphore(SEM_LIMIT)
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            fetch_hits(session, sem, client,
                       row["external_id"], row["url"], row["lot_count"])
            for _, row in df.iterrows()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    total_actual = int(df["lot_count"].sum())
    total_expected = 0
    false_count = 0
    detailed_rows = []

    for r in results:
        if isinstance(r, Exception):
            continue
        detailed_rows.append(r)
        total_expected += r["hits"]
        if not r["match"]:
            false_count += 1

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow(["metric", "value"])
        writer.writerow(["false_count", false_count])
        writer.writerow(["total_expected_count", total_expected])
        writer.writerow(["total_actual_count", total_actual])
        writer.writerow([])

        writer.writerow(["external_id", "hits", "lot_count", "match"])
        for row in detailed_rows:
            writer.writerow([
                row["external_id"],
                row["hits"],
                row["lot_count"],
                row["match"]
            ])

    print(f"Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())