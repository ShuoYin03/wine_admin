import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def fetch_listing_urls(session, url):
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            auction_links = soup.select("a.btn[href*='/wine-auctions/'][href$='/lots']")
            return [link['href'] for link in auction_links]
        else:
            print(f"Failed to fetch {url}: {response.status}")
            return []

async def fetch_hits(session, sem, url):
    async with sem:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                span = soup.find("span", class_="result-summary")
                external_id = soup.find("h1", class_="page-title").text.replace(" ", "-").lower()
                if span:
                    text = span.get_text(strip=True)
                    match = re.search(r"(\d+)\s*-\s*(\d+)\s*of\s*(\d+)\s*Lots", text)
                    if match:
                        _, _, total = match.groups()
                        return (int(total), external_id)
            else:
                print(f"Failed to fetch {url}: {response.status}")
                return []

async def main():
    report = AuctionScrapingReportGenerator("Wineauctioneer")

    auction_lots_data = report.load_lot_counts_from_db()

    sem = asyncio.Semaphore(SEM_LIMIT)
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        initial_urls = [
            f"https://wineauctioneer.com/wine-auctions?page=0,{idx},0,0,0#past-auctions"
            for idx in range(0, 3)
        ]
        
        results = await asyncio.gather(
            *[fetch_listing_urls(session, url) for url in initial_urls]
        )

        all_urls = [url for sublist in results for url in sublist]

        base_url = "https://wineauctioneer.com"
        results = await asyncio.gather(
            *[fetch_hits(session, sem, f"{base_url}{url}") for url in all_urls]
        )

        for result in results:
            if result:
                total, external_id = result
                for lot in auction_lots_data:
                    if lot['external_id'] == external_id:
                        lot_count = lot['lot_count']
                        url = lot['url']
                        match = total == lot_count

                        report.add_result(
                            external_id=external_id,
                            hits=total,
                            lot_count=lot_count,
                            match=match,
                            url=url
                        )
                        break

        report.export()

if __name__ == "__main__":
    asyncio.run(main())