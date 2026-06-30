import os
import scrapy
import dotenv
import asyncio
from datetime import datetime
import pandas as pd
from io import BytesIO
from bs4 import BeautifulSoup
from collections import defaultdict
from shared.database.auctions_client import AuctionsClient
from wine_spider.services import ZachysClient
from wine_spider.services.lot_information_finder import LotInformationFinder
from wine_spider.items import AuctionItem, LotItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.helpers import (
    symbol_to_currency, 
    remove_commas,
    expand_to_lot_items,
    parse_volume,
    producer_to_country,
    region_to_country,
    extract_lot_detail_info,
    combine_volume,
    build_lot_external_id,
)
from wine_spider.spiders.reports.generate_zachys_report import (
    DEFAULT_ZACHYS_REPORT_MAX_PAGES,
    build_zachys_auction_list_url,
    build_zachys_catalog_url,
    extract_zachys_auction_rows,
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ZachysSpider(BaseAuctionSpider):
    name = "zachys_spider"
    allowed_domains = [
        "auction.zachys.com",
        "bid.zachys.com",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": build_spider_log_file("zachys.log"),
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 5,
        "DOWNLOAD_TIMEOUT": 90,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        # "JOBDIR": "wine_spider/crawl_state/zachys",
        "DOWNLOADER_MIDDLEWARES": {
            "wine_spider.middlewares.aws_waf_bypass.AwsWafBypassMiddleware": 543,
        },
        
        "AWS_WAF_MAX_RETRIES": 2,
        "AWS_WAF_MIN_DELAY": 3000,
        "AWS_WAF_MAX_DELAY": 3000,
        "AWS_WAF_RETRY_BASE_DELAY": 30,
        "AWS_WAF_RETRY_MAX_DELAY": 180,
        "AWS_WAF_CLOSE_SPIDER_ON_BLOCK": True,
        "AWS_WAF_BLOCK_STATUSES": [202, 403, 429],
        "AWS_WAF_COOKIES_FILE": "wine_spider.login_state.zachys_cookies.json",
        "AWS_WAF_TOKENS_FILE": "wine_spider.login_state.zachys_tokens.json",
        "AWS_WAF_ENABLED_SPIDERS": ["zachys_spider"],
        
        "PLAYWRIGHT_CONTEXTS": {
            "zachys": {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
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
        self.lot_information_finder = LotInformationFinder()
        self.auction_client = AuctionsClient()
        self.max_pages = int(os.getenv("ZACHYS_SPIDER_MAX_PAGES", str(DEFAULT_ZACHYS_REPORT_MAX_PAGES)))

        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def start(self):
        url = build_zachys_auction_list_url(1, status=5)
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            meta={
                "playwright": True,
                "playwright_context": "zachys",
                "playwright_include_page": True,
                "current_page": 1,
            },
            dont_filter=True,
        )

    async def parse(self, response):
        page = response.meta.get("playwright_page")
        current_page = int(response.meta.get("current_page", 1))
        try:
            auction_rows = extract_zachys_auction_rows(response.text)
            self.logger.info(
                "Found %s Zachys past auctions on listing page %s",
                len(auction_rows),
                current_page,
            )

            for auction_data in auction_rows:
                auction_id = str(auction_data.get("id") or "").strip()
                auction_seo_name = auction_data.get("auction_seo_url") or ""
                if not auction_id:
                    continue

                auction_item = self.build_auction_item(auction_data)
                if self.should_skip_existing_auction(auction_item["external_id"], self.auction_client):
                    continue
                expected_lot_count = self.parse_expected_lot_count(auction_data)

                yield auction_item

                url = self.zachys_client.get_lots_url(
                    auction_id=auction_id,
                    auction_seo_name=auction_seo_name,
                )

                yield scrapy.Request(
                    url=url,
                    callback=self.get_excel_and_info,
                    meta={
                        "playwright": True,
                        "playwright_context": "zachys",
                        "playwright_include_page": True,
                        "auction_id": auction_item["external_id"],
                        "catalog_id": auction_id,
                        "auction_seo_name": auction_seo_name,
                        "expected_lot_count": expected_lot_count,
                    },
                    dont_filter=True,
                )

            if auction_rows and current_page < self.max_pages:
                next_page = current_page + 1
                yield scrapy.Request(
                    url=build_zachys_auction_list_url(next_page, status=5),
                    callback=self.parse,
                    meta={
                        "playwright": True,
                        "playwright_context": "zachys",
                        "playwright_include_page": True,
                        "current_page": next_page,
                    },
                    dont_filter=True,
                )
        finally:
            if page:
                await page.close()

    def build_auction_item(self, auction_data):
        auction_id = str(auction_data.get("id") or "").strip()
        start_date = self.parse_zachys_datetime(auction_data.get("start_date"))
        end_date = self.parse_zachys_datetime(auction_data.get("end_date"))
        auction_item = AuctionItem()
        auction_item["external_id"] = f"zachys_{auction_id}"
        auction_item["auction_title"] = auction_data.get("name")
        auction_item["auction_house"] = "Zachys"
        auction_item["city"] = auction_data.get("cauction_listing_location")
        auction_item["continent"] = "North America"
        auction_item["start_date"] = start_date
        auction_item["end_date"] = end_date
        auction_item["year"] = start_date[:4] if start_date else None
        auction_item["quarter"] = (int(start_date[5:7]) - 1) // 3 + 1 if start_date else None
        auction_item["auction_type"] = "PAST"
        auction_item["url"] = build_zachys_catalog_url(
            auction_id,
            auction_data.get("auction_seo_url") or "",
        )
        return auction_item

    @staticmethod
    def parse_zachys_datetime(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value)).date().isoformat()
        except ValueError:
            return str(value).split(" ")[0]

    @staticmethod
    def parse_expected_lot_count(auction_data):
        try:
            return int(auction_data.get("total_lots") or 0)
        except (TypeError, ValueError):
            return None
    
    async def get_excel_and_info(self, response):
        page = response.meta.get("playwright_page")
        auction_id = response.meta.get("auction_id")
        catalog_id = response.meta.get("catalog_id")
        current_page = response.meta.get("current_page", 1)
        lots = response.meta.get("lots", {})
        auction_seo_name = response.meta.get("auction_seo_name", "")
        expected_lot_count = response.meta.get("expected_lot_count")
        
        try:
            if not lots:
                lots = defaultdict(self.build_empty_lot_record)
                
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
                            "skip_waf_page_methods": True,
                            "lots": lots,
                            "auction_id": auction_id,
                            "expected_lot_count": expected_lot_count,
                        },
                        dont_filter=True
                    )
                    return
                else:
                    self.logger.debug("Excel link not found on the page")
                    return
                
            for lot in soup.find_all("div", class_="list-cols info-col"):
                lot_link = lot.select_one("a.auc-lot-link")
                if not lot_link:
                    self.logger.debug(
                        "Skipping Zachys lot block without lot link in auction %s page %s",
                        auction_id,
                        current_page,
                    )
                    continue

                lot_item = LotItem()
                lot_id = lot_link.get_text(strip=True).strip().split("#")[-1]
                if not lot_id:
                    continue

                lot_item['auction_id'] = auction_id
                lot_item['external_id'] = build_lot_external_id(auction_id, lot_id)
                currency_el = lot.select_one("span[class^=scur]")
                currency = currency_el.get_text(strip=True).strip() if currency_el else None
                lot_item['original_currency'] = symbol_to_currency(currency) if currency else None

                price_info = lot.select_one("li.item-win-bid")
                if price_info:
                    end_price_el = price_info.select_one("span.exratetip")
                    if end_price_el:
                        end_price = end_price_el.extract().get_text(strip=True)
                        if end_price:
                            lot_item['end_price'] = float(remove_commas(end_price))
                            lot_item['sold'] = True

                lots[lot_id]['lot_item'] = lot_item

            url = self.zachys_client.get_lots_url(
                auction_id=catalog_id,
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
                    "catalog_id": catalog_id,
                    "auction_seo_name": auction_seo_name,
                    "current_page": current_page + 1,
                    "lots": lots,
                    "expected_lot_count": expected_lot_count,
                },
                dont_filter=True
            )
        except Exception as e:
            self.logger.error(f"Error fetching Excel and info: {e}")
        finally:
            if page:
                await page.close()

    async def parse_excel(self, response):
        page = response.meta.get("playwright_page")
        lots = response.meta.get("lots", {})
        auction_id = response.meta.get("auction_id")
        expected_lot_count = self.clean_expected_lot_count(
            response.meta.get("expected_lot_count")
        )

        try:
            df = pd.read_excel(BytesIO(response.body), sheet_name='Sheet1', engine='xlrd', header=2)
        except Exception as e:
            self.logger.error(f"Error reading Zachys Excel file for auction {auction_id}: {e}")
            if page:
                await page.close()
            return

        try:
            excel_lot_ids = set()
            for index, row in df.iterrows():
                try:
                    lot_id = self.clean_lot_number(row.get("Lot"))
                    if not lot_id:
                        continue
                    if (
                        expected_lot_count
                        and lot_id not in excel_lot_ids
                        and len(excel_lot_ids) >= expected_lot_count
                    ):
                        self.logger.warning(
                            "Skipping Zachys lot %s in auction %s because expected lot count is %s",
                            lot_id,
                            auction_id,
                            expected_lot_count,
                        )
                        continue

                    if lot_id not in lots:
                        lots[lot_id] = self.build_empty_lot_record()
                    lot_record = lots[lot_id]
                    lot_item = lot_record.get("lot_item")
                    if lot_item is None:
                        lot_item = LotItem()
                        lot_item["auction_id"] = auction_id
                        lot_item["external_id"] = build_lot_external_id(auction_id, lot_id)
                        lot_record["lot_item"] = lot_item

                    excel_lot_ids.add(lot_id)
                    lot_detail_info = lot_record["lot_detail_info"]
                    lot_title = self.clean_excel_value(row.get("Lot Title"))
                    size = self.clean_excel_text(row.get("Size"))
                    lot_details = self.clean_excel_text(row.get("Lot Details"))
                    qty = self.clean_excel_value(row.get("Qty"))
                    region = self.clean_excel_value(row.get("Region"))
                    country = self.clean_excel_value(row.get("Country"))
                    producer = self.clean_excel_value(row.get("Producer"))
                    vintage = self.clean_excel_value(row.get("Vintage"))
                    wine_class = self.clean_excel_value(row.get("Class"))

                    lot_item['lot_name'] = lot_title
                    lot_item['lot_type'] = "Wine & Spirits"
                    if size.lower() == "mixed":
                        lot_volume_detail = extract_lot_detail_info(lot_details, mode="volume")
                        lot_item['volume'] = combine_volume(lot_volume_detail)
                        for _, unit_size in lot_volume_detail:
                            lot_detail_info['unit_format'].append(unit_size)
                    elif size:
                        try:
                            parsed_volume = parse_volume(size)
                            lot_item['volume'] = qty * parsed_volume if qty is not None else parsed_volume
                        except Exception as e:
                            self.logger.warning(
                                "Could not parse Zachys volume %r for lot %s in auction %s: %s",
                                size,
                                lot_id,
                                auction_id,
                                e,
                            )
                        lot_detail_info['unit_format'].append(size)

                    lot_item['unit'] = qty
                    lot_item['low_estimate'] = self.clean_excel_value(row.get("Low Estimate"))
                    lot_item['high_estimate'] = self.clean_excel_value(row.get("High Estimate"))
                    lot_item['region'] = region
                    lot_item['country'] = country
                    if not country:
                        lot_item['country'] = region_to_country(region) or producer_to_country(producer)
                    lot_item['success'] = True
                    lot_item['url'] = self.clean_excel_value(row.get("URL"))

                    if vintage == "Mixed":
                        lot_vintage_detail = extract_lot_detail_info(lot_details, mode="vintage")
                        lot_detail_info['vintage'].extend(lot_vintage_detail)
                    elif vintage:
                        lot_detail_info['vintage'].append(vintage)

                    if producer:
                        lot_detail_info['lot_producer'].append(producer)
                    if wine_class:
                        lot_detail_info['wine_colour'].append(wine_class)
                except Exception as e:
                    self.logger.error(
                        "Error parsing Zachys Excel row %s for auction %s: %s",
                        index,
                        auction_id,
                        e,
                    )

            for lot_id, lot in lots.items():
                if lot_id not in excel_lot_ids:
                    continue
                if not lot["lot_item"]:
                    continue

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
        except Exception as e:
            self.logger.error(f"Error parsing Excel file: {e}")
        finally:
            if page:
                await page.close()

    @staticmethod
    def build_empty_lot_record():
        return {
            "lot_item": None,
            "lot_detail_info": {
                k: [] for k in [
                    "lot_producer",
                    "vintage",
                    "unit_format",
                    "wine_colour",
                ]
            },
        }

    @staticmethod
    def clean_excel_value(value):
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        return value

    @classmethod
    def clean_excel_text(cls, value) -> str:
        value = cls.clean_excel_value(value)
        return "" if value is None else str(value).strip()

    @classmethod
    def clean_lot_number(cls, value) -> str:
        value = cls.clean_excel_value(value)
        if value is None:
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def clean_expected_lot_count(value):
        try:
            parsed = int(value or 0)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")
