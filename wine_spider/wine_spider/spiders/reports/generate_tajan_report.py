import re
import asyncio
import unicodedata
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

SEM_LIMIT = 10

def generate_external_id(title: str) -> str:
    title = title.lower()
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    title = re.sub(r'\s*[\-&xX]+\s*', ' ', title)
    title = re.sub(r'[^a-z0-9\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    slug = title.replace(' ', '-')
    return slug

async def extract_listing_urls(page):
    base_url = "https://www.tajan.com/en/past/"
    await page.goto(base_url)
    results = []
    count = 0
    match_count = 0
    while True:
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        auction_blocks = soup.select("div#plab__results-container div.widget-event")
        for auction in auction_blocks:
            title_tag = auction.select_one("h2.event__title a")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True).lower()
            count += 1

            if "wine" in title or "spirits" in title:
                match_count += 1
                raw_date = auction.select_one("div.event__date").get_text(strip=True)
                raw_time = auction.select_one("div.event__time.mb-0").get_text(strip=True) if auction.select_one("div.event__time.mb-0") else ""
                url = title_tag.get("href") 
                results.append((url, f"tajan_{generate_external_id(f"{title} {raw_date} {raw_time}")}"))

        next_page_link = soup.select_one("a.next.pagination")
        if not next_page_link:
            break
        next_href = next_page_link.get("href")
        if not next_href:
            break
        await page.goto(next_href)

    return results

async def fetch_hits(page, url, report):
    try:
        await page.goto(url, timeout=60000)
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        auction_link = None
        for a in soup.select("div.sale-ctas a"):
            text = a.get_text(strip=True)
            href = a.get("href")
            if href and href.startswith("https://www.calameo.com"):
                continue
            if text and (
            "view auction" in text.lower() or
            "browse lots" in text.lower() or
            "view lots" in text.lower() or
            "view lot" in text.lower()):
                auction_link = href
                break
        
        if auction_link:
            await page.goto(auction_link, timeout=60000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            hits_tag = soup.select_one("div#catLotCountInfoM")

            hits = hits_tag.get_text(strip=True) if hits_tag else None
            hits = int(hits.replace(" lots", "").replace("lots", "").replace(" Lots", "").replace("Lots", "")) if hits else 0
            return hits
        else:
            hits_tag = soup.select_one("div#catLotCountInfoM")
            if not hits_tag:
                print(f"[ERROR] No hits found or no valid auction link for {url}")
                return
            hits = hits_tag.get_text(strip=True) if hits_tag else None
            hits = int(hits.replace(" lots", "").replace("lots", "").replace(" Lots", "").replace("Lots", "")) if hits else 0
            return hits
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")

async def main():
    report = AuctionScrapingReportGenerator("Tajan")

    sem = asyncio.Semaphore(SEM_LIMIT)
    auction_lots_data = report.load_lot_counts_from_db()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
            java_script_enabled=True
        )

        page = await browser.new_page()
        listing_urls = await extract_listing_urls(page)
        await page.close()

        async def process_url(url, external_id):
            async with sem:
                page = await browser.new_page()
                hits = await fetch_hits(page, url, report)
                await page.close()
                
                if hits:
                    found = False
                    for lot in auction_lots_data:
                        if lot["external_id"] == external_id:
                            lot_count = lot.get("lot_count", 0)
                            url = lot.get("url", url)
                            match = hits == lot_count
                            
                            report.add_result(
                                external_id=external_id,
                                hits=hits,
                                lot_count=lot_count,
                                match=match,
                                url=url,
                            )

                            found = True
                            break
                    
                    if not found:
                        report.add_result(
                            external_id=external_id,
                            hits=hits,
                            lot_count=0,
                            match=False,
                            url=url,
                        )

        await asyncio.gather(*(process_url(url, external_id) for url, external_id in listing_urls))
        await browser.close()

    report.export()

if __name__ == "__main__":
    asyncio.run(main())