import os
import re
import json
import scrapy
import dotenv
import asyncio
from bs4 import BeautifulSoup
from wine_spider.services import ZachysClient
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.spiders.reports.auction_scraping_report_generator import AuctionScrapingReportGenerator

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ZachysReportSpider(scrapy.Spider):
    name = "zachys_report_spider"
    allowed_domains = [
        "bid.zachys.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": build_spider_log_file("zachys_report.log"),
        "DOWNLOADER_MIDDLEWARES": {
            "wine_spider.middlewares.aws_waf_bypass.AwsWafBypassMiddleware": 543,
        },
        
        "AWS_WAF_MAX_RETRIES": 5,
        "AWS_WAF_MIN_DELAY": 2000,
        "AWS_WAF_MAX_DELAY": 5000,
        "AWS_WAF_COOKIES_FILE": "wine_spider.login_state.zachys_cookies.json",
        "AWS_WAF_TOKENS_FILE": "wine_spider.login_state.zachys_tokens.json",
        "AWS_WAF_ENABLED_SPIDERS": ["zachys_spider"],
        
        "PLAYWRIGHT_CONTEXTS": {
            "zachys": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Cache-Control": "max-age=0"
                },
                "device_scale_factor": 1,
                "is_mobile": False,
                "has_touch": False,
                "bypass_csp": True
            }
        }
    }

    def __init__(self, *args, **kwargs):
        super(ZachysReportSpider, self).__init__(*args, **kwargs)
        self.zachys_client = ZachysClient()
        self.report = AuctionScrapingReportGenerator("Zachys")
        self.lot_counts_from_db = self.report.load_lot_counts_from_db()

        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    def start_requests(self):
        max_page = 3
        for page in range(0, max_page + 1):
            url = f"https://bid.zachys.com/auctions?page={page}&status=5"

            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_context": "zachys",
                    "playwright_include_page": True,
                },
                dont_filter=True
            )
            print(f"Requesting page {page}: {url}")

    async def parse(self, response):
        page = response.meta.get("playwright_page")
        
        try:
            if "container" in response.text and "challenge-container" not in response.text:
                print(f"Successfully loaded page content for {response.url}")
                
                soup = BeautifulSoup(response.body, "html.parser")
                script_text = soup.find("script", string=re.compile("auctionRows")).string
                match = re.search(r"auctionRows\"\s*,\s*(\[\{.*?\}\])\);", script_text, re.DOTALL)
                if not match:
                    raise ValueError("auctionRows JSON not found")
                
                auction_data_raw = match.group(1)
                auction_datas = json.loads(auction_data_raw)

                for auction_data in auction_datas:
                    print(f"Processing auction: {auction_data.get('id')} - {auction_data.get('title')}")
                    external_id = f"zachys_{auction_data.get("id")}"

                    url = self.zachys_client.get_lots_url(
                        auction_id=auction_data.get("id"),
                        auction_seo_name=auction_data.get("auction_seo_url"),
                    )

                    yield scrapy.Request(
                        url=url,
                        callback=self.add_results,
                        meta={
                            "playwright": True,
                            "playwright_context": "zachys",
                            "playwright_include_page": True,
                            "auction_id": external_id,
                        },
                        dont_filter=True
                    )
                
            else:
                print(f"Page not fully loaded or still on challenge page: {response.url}")

        except Exception as e:
            print(f"Error parsing page: {e}")

        finally:
            if page:
                await page.close()
    
    async def add_results(self, response):
        page = response.meta.get("playwright_page")
        auction_id = response.meta.get("auction_id")
        
        try:    
            soup = BeautifulSoup(response.body, "html.parser")
            hits_div = soup.find("div", class_="page")
            hits = int(hits_div.get_text(strip=True).split('\xa0')[-1].split(".")[0])

            found = False
            for lot in self.lot_counts_from_db:
                if lot["external_id"] == auction_id:
                    lot_count = lot["lot_count"]
                    url = lot["url"]
                    match = lot_count == hits
                    found = True
                    self.report.add_result(
                        external_id=auction_id,
                        hits=hits,
                        lot_count=lot_count,
                        match=match,
                        url=url
                    )

                    break

            if not found:
                self.report.add_result(
                    external_id=auction_id,
                    hits=hits,
                    lot_count=0,
                    match=False,
                    url=response.url
                )

        except Exception as e:
            print(f"Error fetching Excel and info: {e}")
        finally:
            if page:
                await page.close()

    def closed(self, reason):
        self.report.export()
