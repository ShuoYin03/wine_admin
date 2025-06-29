import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from tools.scraping_report.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def fetch_hits(session, sem, url):
    async with sem:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                ul = soup.find("ul", class_="infos text-uppercase")
                if ul:
                    li_elements = ul.find_all("li")
                    if li_elements:
                        last_li = li_elements[-1]
                        external_id_text_split = li_elements[3].text.strip().split(" ")
                        external_id = "".join(external_id_text_split[1:])
                        match = re.search(r'(\d+)\s+Lots', last_li.text)
                        if match:
                            lots_count = int(match.group(1))
                            print(f"Found {lots_count} lots for external_id: {external_id}")
                            return lots_count, external_id
                        else:
                            print(f"No match found in last li: {last_li.text}")
                            return 0, external_id
            else:
                print(f"Failed to fetch {url}: {response.status}")
                return []

async def main():
    report = AuctionScrapingReportGenerator("Baghera")

    auction_lots_data = report.load_lot_counts_from_db()

    sem = asyncio.Semaphore(SEM_LIMIT)
    connector = aiohttp.TCPConnector(limit=SEM_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with sem:
            async with session.get("https://www.bagherawines.auction/en/catalogue/archive") as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    auction_links = soup.select("div.col-8 a")
                    all_urls = [a.get("href") for a in auction_links if a.get("href")]
                    
                else:
                    print(f"Failed to fetch auction listing: {response.status}")
                    return

        results = await asyncio.gather(
            *[fetch_hits(session, sem, url) for url in all_urls]
        )

        for result in results:
            if result:
                hits, external_id = result
                for lot in auction_lots_data:
                    if lot['external_id'] == external_id:
                        lot_count = lot['lot_count']
                        url = lot['url']
                        match = hits == lot_count
                        print(f"Processing {external_id}: hits={hits}, lot_count={lot_count}, match={match}, url={url}")
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