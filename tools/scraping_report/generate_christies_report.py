from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator
import asyncio
import aiohttp
import re
import json
import demjson3
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def extract_lots_page_urls(html: str) -> Optional[list[str]]:
    urls = []

    match = re.search(r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n', html, re.DOTALL)
    if not match:
        return

    data = demjson3.decode(match.group(1))
    events = data.get('data', {}).get('events', [])

    for event in events:
        filters = event.get("filter_ids", "")


        if "category_14" in filters:
            url = event.get("landing_url", None)
            try:
                if "onlineonly.christies.com" in url:
                    parsed = urlparse(url)
                    qs = parse_qs(parsed.query)
                    sale_id = qs.get("SaleID", [None])[0]
                    sale_number = qs.get("SaleNumber", [None])[0]
                elif "www.christies.com" in url:
                    sale_id = int(url.split("/")[-2].split("-")[-1])
                    sale_number_text = event.get("subtitle_txt", None)
                    sale_number = int(sale_number_text.split(" ")[2])

                urls.append((url, sale_id, sale_number))
            except (ValueError, IndexError):
                print(f"Error parsing URL: {url}")
                continue
            
    return urls

async def fetch_hits(session, sem, url, sale_id, sales_number):
    if url.split("/")[-1].strip().isdigit():
        sale_id = int(url.split("/")[-1].strip())

    async with sem:
        async with session.get(url) as response:
            if response.status == 200:
                try:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    dropdown = soup.find("chr-dropdown")
                    if not dropdown:
                        return
                    action_items_raw = dropdown.get("action-items")
                    action_items = json.loads(action_items_raw)
                    for item in action_items:
                        label = item.get("label", "")
                        match = re.search(r'Browse lots\s*\((\d+)\)', label)
                        if match:
                            return (int(match.group(1)), sale_id, sales_number)
                except Exception as e:
                    print(url, "Error:", e)

async def fetch_listing_urls(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                return extract_lots_page_urls(html)
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

async def main():
    report = AuctionScrapingReportGenerator("Christie's")

    auction_lots_data = report.load_lot_counts_from_db()
    conn = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=conn) as session:

        listing_urls = [
            f"https://www.christies.com/en/results?year={y}&filters=|category_14|&month={m}"
            for y in range(2007, 2026)
            for m in range(1, 13)
        ]

        results = await asyncio.gather(
            *[fetch_listing_urls(session, url) for url in listing_urls]
        )

        all_urls = [(url, sales_id, sales_number) for sublist in results if sublist for url, sales_id, sales_number in sublist]
        
        sem = asyncio.Semaphore(10)
        counts = await asyncio.gather(
            *[fetch_hits(session, sem, url, sales_id, sales_number) for url, sales_id, sales_number in all_urls]
        )
        counts = [count for count in counts if count is not None]
        for count, sales_id, sales_number in counts:
            # if count is not None:
            for lot in auction_lots_data:
                if lot['external_id'] == f"{sales_id}#{sales_number}":
                    report.add_result(
                        external_id=f"{sales_id}#{sales_number}",
                        hits=count,
                        lot_count=lot['lot_count'],
                        match=count == lot['lot_count'],
                        url=lot['url']
                    )

                    break

    report.export()


if __name__ == "__main__":
    asyncio.run(main())