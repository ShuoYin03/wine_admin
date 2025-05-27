import os
import re
import json
import scrapy
import dotenv
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
from collections import defaultdict
from wine_spider.services import ZachysClient
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import (
    symbol_to_currency, 
    remove_commas,
    expand_to_lot_items,
    parse_volume,
    producer_to_country,
    region_to_country,
    extract_lot_detail_info,
    combine_volume,
    make_serializable
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ZachysSpider(scrapy.Spider):
    name = "zachys_spider"
    allowed_domains = [
        "bid.zachys.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "zachys_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/zachys",
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
        super(ZachysSpider, self).__init__(*args, **kwargs)
        self.zachys_client = ZachysClient()

    def start_requests(self):
        max_page = 1
        for page in range(1, max_page + 1):
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

    async def parse(self, response):
        page = response.meta.get("playwright_page")
        
        if "container" in response.text and "challenge-container" not in response.text:
            self.logger.info("Successfully loaded page content!")
            
            soup = BeautifulSoup(response.body, "html.parser")
            script_text = soup.find("script", string=re.compile("auctionRows")).string
            match = re.search(r"auctionRows\"\s*,\s*(\[\{.*?\}\])\);", script_text, re.DOTALL)
            if not match:
                raise ValueError("auctionRows JSON not found")
            
            auction_data_raw = match.group(1)
            auction_datas = json.loads(auction_data_raw)

            for auction_data in auction_datas[:1]:
                auction_item = AuctionItem()
                auction_item['external_id'] = f"zachys_{auction_data.get("id")}"
                auction_item['auction_title'] = auction_data.get("name")
                auction_item['auction_house'] = "Zachys"
                auction_item['city'] = auction_data.get("location")
                auction_item['continent'] = "North America"
                auction_item['start_date'] = auction_data.get("start_date")
                auction_item['end_date'] = auction_data.get("end_date")
                auction_item['year'] = auction_item['start_date'].split("-")[0]
                auction_item['quarter'] = int(auction_item['start_date'].split("-")[1]) // 4 + 1 if auction_item['start_date'].split("-")[1] else None
                auction_item['auction_type'] = auction_data.get("type")
                auction_item['url'] = auction_data.get("url")
                # yield auction_item

                url = self.zachys_client.get_lots_url(
                    auction_id=auction_data.get("id"),
                    auction_seo_name=auction_data.get("auction_seo_url"),
                )

                yield scrapy.Request(
                    url=url,
                    callback=self.get_excel_and_info,
                    meta={
                        "playwright": True,
                        "playwright_context": "zachys",
                        "playwright_include_page": True,
                        "auction_id": auction_data.get("id"),
                        "auction_seo_name": auction_data.get("auction_seo_url")
                    },
                    dont_filter=True
                )
            
        else:
            self.logger.warning(f"Page not fully loaded or still on challenge page: {response.url}")
        
        if page:
            await page.close()
    
    def get_excel_and_info(self, response):
        auction_id = response.meta.get("auction_id")
        current_page = response.meta.get("current_page", 1)
        lots = response.meta.get("lots", {})
        auction_seo_name = response.meta.get("auction_seo_name", "")

        if not lots:
            lots = defaultdict(
                lambda: {
                    "lot_item": None, 
                    "lot_detail_info": {
                        k: [] for k in [
                            "lot_producer", 
                            "vintage", 
                            "unit_format", 
                            "wine_colour"
                        ]}})
            
        soup = BeautifulSoup(response.body, "html.parser")
        html_info = soup.find_all("div", class_="list-cols info-col")
        if not html_info:
            excel_doc = soup.find("a", class_="excel_doc")
            if excel_doc:
                excel_link = excel_doc.get("href")

                yield scrapy.Request(
                    url=excel_link,
                    callback=self.parse_excel,
                    meta={
                        "playwright": True,
                        "playwright_context": "zachys",
                        "playwright_include_page": True,
                        "lots": lots,
                        "auction_id": auction_id
                    },
                    dont_filter=True
                )
                return
            else:
                self.logger.debug("Excel link not found on the page")
                return
            
        for lot in soup.find_all("div", class_="list-cols info-col"):
            lot_item = LotItem()
            lot_id = lot.select_one("a.auc-lot-link").extract().text.strip().split("#")[-1]
            lot_item['external_id'] = f"zachys_{auction_id}_{lot_id}"
            currency = lot.select_one("span[class^=scur]").extract().text.strip()
            lot_item['original_currency'] = symbol_to_currency(currency) if currency else None

            price_info = lot.select_one("li.item-win-bid")
            if price_info:
                end_price = price_info.select_one("span.exratetip").extract().text.strip()
                lot_item['end_price'] = float(remove_commas(end_price))
                lot_item['sold'] = True

            lots[lot_id]['lot_item'] = lot_item

        url = self.zachys_client.get_lots_url(
            auction_id=auction_id,
            auction_seo_name=auction_seo_name,
            page=current_page+1
        )

        yield scrapy.Request(
            url=url,
            callback=self.get_excel_and_info,
            meta={
                "playwright": True,
                "playwright_context": "zachys",
                "playwright_include_page": True,
                "auction_id": auction_id,
                "auction_seo_name": auction_seo_name,
                "current_page": current_page + 1,
                "lots": lots
            },
            dont_filter=True
        )
    
    async def parse_excel(self, response):
        page = response.meta.get("playwright_page")
        lots = response.meta.get("lots", {})
        auction_id = response.meta.get("auction_id")
        
        df = pd.read_excel(BytesIO(response.body), sheet_name='Sheet1', engine='xlrd', header=2)
        for index, row in df.iterrows():
            lot_item = lots[str(row.get("Lot"))]['lot_item']
            lot_detail_info = lots[str(row.get("Lot"))]['lot_detail_info']

            lot_item['lot_name'] = row.get("Lot Title")
            lot_item['lot_type'] = "Wine & Spirits"
            if row.get("Size") == "Mixed":
                lot_volume_detail = extract_lot_detail_info(row.get("Lot Details"), mode="volume")
                lot_item['volume'] = combine_volume(extract_lot_detail_info(row.get("Lot Details"), mode="volume"))
                for _, size in lot_volume_detail:
                    lot_detail_info['unit_format'].append(size)
            else:
                lot_item['volume'] = row.get("Qty") * parse_volume(row.get("Size"))
                lot_detail_info['unit_format'].append(row.get("Size"))
            lot_item['unit'] = row.get("Qty")
            lot_item['low_estimate'] = row.get("Low Estimate")
            lot_item['high_estimate'] = row.get("High Estimate")
            lot_item['region'] = row.get("Region")
            lot_item['country'] = row.get("Country")
            if not row.get("Country") or pd.isna(row.get("Country")):
                country = region_to_country(row.get("Region")) or producer_to_country(row.get("Producer")) 
                lot_item['country'] = country
            lot_item['success'] = True
            lot_item['url'] = row.get("URL")

            if row.get("Vintage") == "Mixed":
                lot_vintage_detail = extract_lot_detail_info(row.get("Lot Details"), mode="vintage")
                lot_detail_info['vintage'].extend(lot_vintage_detail)
            else:
                lot_detail_info['vintage'].append(row.get("Vintage"))
            lot_detail_info['lot_producer'].append(row.get("Producer"))
            lot_detail_info['wine_colour'].append(row.get("Class"))

        # serializable_lots = make_serializable(lots)

        # with open("lots.json", "w") as f:
        #     json.dump(serializable_lots, f, indent=4)
        
        for lot in lots.values():
            if not lot['lot_detail_info']['lot_producer'] or lot['lot_detail_info']['lot_producer'] == []:
                try:
                    producer, _, _, _ =  self.lot_information_finder.find_lot_information(lot["lot_item"]["lot_name"])
                    lot['lot_detail_info']['lot_producer'].append(producer)
                except Exception as e:
                    self.logger.error(f"Error finding lot information: {e} for lot {lot['lot_item']['external_id']} in auction {auction_id}")
                    lot['lot_item']['success'] = False

            yield lot["lot_item"]

            lot_detail_info = lot["lot_detail_info"]
            lot_detail_items = expand_to_lot_items(
                lot_producer=lot_detail_info["lot_producer"],
                vintage=lot_detail_info["vintage"],
                unit_format=lot_detail_info["unit_format"],
                wine_colour=lot_detail_info["wine_colour"]
            )

            for lot_detail_item in lot_detail_items:
                lot_detail_item["lot_id"] = lot["lot_item"]["external_id"]
                yield lot_detail_item

        if page:
            await page.close()

    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")