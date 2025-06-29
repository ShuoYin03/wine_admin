import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def fetch_hits(session, sem, url, external_id):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with sem:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        soup = BeautifulSoup(await response.text(), 'html.parser')

                        hits_text = soup.find("p", class_="items_found").text.strip()
                        hits_match = re.search(r"(\d+)\s+lots\s+found", hits_text)
                        if hits_match:
                            hits = int(hits_match.group(1))
                            return (external_id, hits)
                    else:
                        print(f"[{external_id}] HTTP {response.status}")
        except Exception as e:
            print(f"[{external_id}] Attempt {attempt} failed: {e}")

        if attempt < MAX_RETRIES:
            sleep_time = RETRY_BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(f"[{external_id}] Retrying in {sleep_time:.1f}s...")
            await asyncio.sleep(sleep_time)

async def main():
    base_url = "https://www.sylvies.be/"

    report = AuctionScrapingReportGenerator("Sylvie's")

    auction_lots_data = report.load_lot_counts_from_db()

    sem = asyncio.Semaphore(SEM_LIMIT)
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        results = []
        async with session.get("https://www.sylvies.be/en/ended-auctions") as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                history_auctions = soup.find_all("div", class_="history")
                results = []

                for history_div in history_auctions:
                    for auction_link_element in history_div.find_all('a', href=re.compile(r"^/en/auction/")):
                        auction_url = auction_link_element['href']
                        if auction_url.startswith("/en/auction/0/"):
                            continue
                        auction_title = auction_link_element.get_text(strip=True)
                        modified_auction_title = auction_title.replace(" ", "-").lower()
                        external_id = f"sylvies_{modified_auction_title}"
                        full_url = f"{base_url.rstrip('/')}{auction_url}"
                        results.append((external_id, full_url))

        results = await asyncio.gather(*[fetch_hits(session, sem, url, external_id) for external_id, url in results])

        for external_id, hits in results:
            if hits is not None:
                for auction in auction_lots_data:
                    if auction['external_id'] == external_id:
                        lot_count = auction['lot_count']
                        url = auction['url']
                        match = lot_count == hits
                        
                        report.add_result(
                            external_id=external_id, 
                            hits=hits, 
                            lot_count=lot_count, 
                            url=url, 
                            match=match
                        )

                        break

        report.export()

if __name__ == "__main__":
    asyncio.run(main())