from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

import os
import re
import json
import time
import scrapy
import dotenv
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
from wine_spider.services import (
    lots_client,
    auctions_client,
)
from wine_spider.services import SothebysClient
from wine_spider.helpers import EnvironmentHelper
from wine_spider.items import AuctionItem, LotItem, LotDetailItem, CombinedLotItem, LwinMatchingItem
from wine_spider.exceptions import (
    NoPreDefinedVolumeIdentifierException, 
    AmbiguousRegionAndCountryMatchException, 
    NoMatchedRegionAndCountryException, 
    WrongMatchedRegionAndCountryException, 
    CityNotFoundException,
    NoVolumnInfoException
)
from wine_spider.helpers import find_continent, region_to_country, parse_quarter, parse_volume_and_unit_from_title, parse_year_from_title, match_lot_info

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH", "False").lower() in ('true', '1', 't')
BASE_URL = os.getenv("BASE_URL")
environmentHelper = EnvironmentHelper()

class SothebysSpider(scrapy.Spider):
    name = "sothebys_spider"
    allowed_domains = [
        "www.sothebys.com", 
        "clientapi.prod.sothelabs.com",
        "kar1ueupjd-2.algolianet.com",
        "algolia.net"
    ]

    custom_settings = {
        "LOG_FILE": "sothebys_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/sothebys",
    }

    start_urls = ["https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q="]

    def __init__(self, *args, **kwargs):
        super(SothebysSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))
        self.base_url = "https://www.sothebys.com"
        self.client = SothebysClient()
        
    def parse(self, response):
        total_pages = int(response.css('li.SearchModule-pageCounts span[data-page-count]::text').get())
        self.logger.info(f"Crawling Total pages: {total_pages}")
        base_url = "https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q=&p={}"
        for page in range(1, 25):
            url = base_url.format(page)
            yield scrapy.Request(
                url=url, 
                callback=self.parse_uuids,
            )

    def parse_uuids(self, response):
        uuids = response.css('.Card-salePrice span::attr(data-dynamic-sale-price-uuid)').getall()
        uuids = ",".join(uuids)
        api_url = f"https://www.sothebys.com/data/api/asset.actions.json?id={uuids}"

        yield scrapy.Request(
            url=api_url,
            method='GET',
            callback=self.parse_viking_ids,
        )
    
    def parse_viking_ids(self, response):
        data = json.loads(response.text)
        data = [(asset_data.get("vikingId"), asset_data.get("url")) for _, asset_data in data.items()]

        for viking_id, url in data:
            if not FULL_FETCH and self.check_exists(viking_id, "auction"):
                self.logger.debug(f"Auction {viking_id} exists, Skipping...")
                continue

            payload = self.client.auction_query(viking_id)
            
            yield scrapy.Request(
                url=self.client.api_url,
                method='POST',
                body=json.dumps(payload),
                callback=self.parse_auction_api_response,
                priority=10,
                meta={
                    "url": url
                },
            )

            yield scrapy.Request(
                url=url,
                method="GET",
                callback=self.after_auth,
                priority=0,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "timeout": 30000,
                        "wait_until": "domcontentloaded"
                    },
                    "playwright_page_close": True,
                    "viking_id": viking_id,
                    "url": url
                }
            )

    async def after_auth(self, response):
        url = response.meta.get("url")
        viking_id = response.meta.get("viking_id")
        page = response.meta["playwright_page"]
        token = None
        token_future = asyncio.Future()

        async def handle_response(response):
            nonlocal token
            if response.url.startswith("https://accounts.sothebys.com/authorize"):
                try:
                    text = await response.text()
                    m = re.search(r'"access_token"\s*:\s*"([^"\\]+)"', text)
                    if m:
                        # token = m.group(1)
                        token_future.set_result(m.group(1))
                except Exception as e:
                    self.logger.error(f"Error extracting token: {e}")

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            try:
                self.logger.debug("Waiting for access_token...")
                token = await asyncio.wait_for(token_future, timeout=15)
                self.logger.debug("Access token received")
            except asyncio.TimeoutError:
                self.logger.error("Timed out waiting for access_token")
                return

            html = await page.content()
            try:
                soup = BeautifulSoup(html, "html.parser")
                pagination = soup.select(".pagination-module_pagination__TRr2-")
                page_count = int(pagination[0].find_all("li")[-2].text) + 1
            except Exception:
                page_count = 1
                self.logger.debug(f"Unable to find page number for the following url: {url}")

            algolia_api_key = self.client.extract_algolia_api_key(html)

            for p in range(page_count):
                algolia_url, algolia_headers, algolia_payload = self.client.algolia_api(viking_id, algolia_api_key, p)
                yield scrapy.Request(
                    url=algolia_url,
                    method="POST",
                    headers=algolia_headers,
                    body=json.dumps(algolia_payload),
                    callback=self.parse_lots_page,
                    meta={
                        "viking_id": response.meta["viking_id"],
                        "token": token
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in after_auth: {e}")
        finally:
            if not page.is_closed():
                await page.close()

    def parse_auction_api_response(self, response):
        url = response.meta.get("url")

        try:
            data = json.loads(response.text)['data']['auction']
            auction_item = AuctionItem()
            auction_item['external_id'] = data['auctionId']
            auction_item['auction_title'] = data['title']
            auction_item['auction_house'] = "Sotheby's"
            auction_item['city'] = data['location']['name']
            auction_item['continent'] = find_continent(data['location']['name'])
            auction_item['start_date'] = data['dates']['acceptsBids'] if 'dates' in data and data['dates'] and 'acceptsBids' in data['dates'] else None
            auction_item['end_date'] = data['dates']['closed']
            auction_item['year'] = int(data['dates']['closed'].split("-")[0]) if data['dates']['closed'] else None
            auction_item['quarter'] = parse_quarter(int(data['dates']['closed'].split("-")[1])) if data['dates']['closed'] else None
            auction_item['auction_type'] = "PAST"
            auction_item['url'] = url
            
            yield auction_item
        except Exception as e:
            self.logger.debug(f"Debugging auction data: {json.loads(response.text)}")
            self.logger.error(f"Failed to parse auction data: {e}")

    def parse_lots_page(self, response):
        viking_id = response.meta.get("viking_id")
        token = response.meta.get("token")
        data = response.json()['hits']

        lots = []
        lot_detail_items = []
        combined_lot_items = []

        for item in data:
            lot = LotItem()
            if not FULL_FETCH and self.check_exists(item['objectID'], "lot"):
                self.logger.info(f"Lot {item['objectID']} exists, Skipping...")
                continue

            lot['external_id'] = item['objectID']
            lot['auction_id'] = item['auctionId']
            lot['lot_name'] = item['title']
            lot['lot_type'] = item['departments']
            lot['original_currency'] = item['currency']
            lot['low_estimate'] = item['lowEstimate']
            lot['high_estimate'] = item['highEstimate']
            if item['lowEstimate'] == -1:
                lot['low_estimate'] = 0
            if item['highEstimate'] == -1:
                lot['high_estimate'] = 0
            lot['region'] = item['Region'][0] if 'Region' in item else None
            lot['country'] = item['Country'][0] if 'Country' in item else None
            lot['success'] = True
            lot['url'] = f"{self.base_url}{item['slug']}"
            try:
                lot['volume'], lot['unit'] = parse_volume_and_unit_from_title(item['title'])
            except (NoPreDefinedVolumeIdentifierException,
                    NoVolumnInfoException) as e:
                lot['volume'], lot['unit'] = None, None
                lot['success'] = False
                self.logger.error(f"Failed to parse lot {item['objectID']}: {e}")

            lot_producer = item["Winery"] if "Winery" in item else item["Distillery"] if "Distillery" in item else []
            vintage = item['Vintage'] if 'Vintage' in item else item['age'] if 'age' in item else []
            unit_format = item['Spirit Bottle Size'] if 'Spirit Bottle Size' in item else []
            wine_colour = item['Wine Type'] if 'Wine Type' in item else []
            if not vintage:
                vintage = [str(parse_year_from_title(item['title']))] if parse_year_from_title(item['title']) else []

            try:
                if not lot_producer or not lot['region'] or not lot['country']:
                    lot_info = match_lot_info(lot['lot_name'], self.lwin_df, lot_producer, lot['region'], lot['country'])
                    lot_producer = [lot_info[0]] if not lot_producer else lot_producer
                    lot['region'] = lot_info[1] if not lot['region'] else lot['region']
                    lot['sub_region'] = lot_info[2]
                    lot['country'] = lot_info[3] if not lot['country'] else lot['country']
                    if lot["region"]:
                        lot["country"] = region_to_country(lot["region"]) if not lot["country"] else lot["country"]
            except (AmbiguousRegionAndCountryMatchException,
                    NoMatchedRegionAndCountryException,
                    WrongMatchedRegionAndCountryException,
                    CityNotFoundException) as e:
                if 'Spirits' not in lot['lot_type']:
                    lot['success'] = False
                    self.logger.error(f"Failed to parse lot {lot['external_id']}: {e}")

            max_length = max(len(lot_producer), len(vintage), len(unit_format), len(wine_colour), 1)
            lot_producer += [lot_producer[0]] * (max_length - len(lot_producer)) if len(lot_producer) == 1 else [None] * (max_length - len(lot_producer))
            vintage += [vintage[0]] * (max_length - len(vintage)) if len(vintage) == 1 else [None] * (max_length - len(vintage))
            unit_format += [unit_format[0]] * (max_length - len(unit_format)) if len(unit_format) == 1 else [None] * (max_length - len(unit_format))
            wine_colour += [wine_colour[0]] * (max_length - len(wine_colour)) if len(wine_colour) == 1 else [None] * (max_length - len(wine_colour))

            for i in range(max_length):
                lot_detail_item = LotDetailItem()
                lot_detail_item['lot_id'] = lot['external_id']
                lot_detail_item['lot_producer'] = lot_producer[i]
                lot_detail_item['vintage'] = vintage[i]
                lot_detail_item['unit_format'] = unit_format[i]
                lot_detail_item['wine_colour'] = wine_colour[i]
                lot_detail_items.append(lot_detail_item)

                combinedLotItem = CombinedLotItem()
                combinedLotItem['lot'] = lot
                combinedLotItem['lot_items'] = lot_detail_item
                combined_lot_items.append(combinedLotItem)

            lots.append(lot)
        
        lot_ids = [lot['external_id'] for lot in lots]
        payload = self.client.lot_card_query(viking_id, lot_ids)

        headers = {
            "Content-Type": "application/json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        yield scrapy.Request(
            url=self.client.api_url,
            method='POST',
            headers=headers,
            body=json.dumps(payload),
            callback=self.parse_lot_api_response,
            meta={
                "lots": lots,
                "lot_items": lot_detail_items,
                "combined_lot_items": combined_lot_items,
            },
        )   

    def parse_lot_api_response(self, response):
        lots = response.meta.get("lots")
        data = json.loads(response.text)['data']['auction']['lot_ids']
        data_dict = {
            item['lotId']: (
                (item['bidState']['startingBid']['amount'], item['bidState']['sold']['premiums']['finalPrice']['amount'], item['bidState']['sold']['isSold'], item['bidState']['closingTime'])
                if item['bidState']['sold']['isSold']
                else (item['bidState']['startingBid']['amount'], item['bidState']['sold']['isSold'], item['bidState']['closingTime'])
            )
            for item in data
        }
        
        for lot in lots:
            if len(data_dict.get(lot['external_id'])) == 4:
                lot['start_price'], lot['end_price'], lot['sold'], lot['sold_date'] = data_dict[lot['external_id']]
            else:
                lot['start_price'], lot['sold'], lot['sold_date'] = data_dict[lot['external_id']]

            yield lot

        for lot_item in response.meta.get("lot_items"):
            yield lot_item

        for combined_lot_item in response.meta.get("combined_lot_items"):
            lot = combined_lot_item['lot']
            lot_items = combined_lot_item['lot_items']

            payload = {
                "wine_name": lot.get('lot_name'),
                "lot_producer": lot_items.get('lot_producer'),
                "vintage": lot_items.get('vintage'),
                "region": lot.get('region'),
                "sub_region": lot.get('sub_region'),
                "country": lot.get('country'),
                "colour": (lot_items.get('wine_colour') or [None])[0]
            }

            yield scrapy.Request(
                url=environmentHelper.get_matching_url(),
                method='POST',
                body=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                callback=self.handle_lwin_response,
                meta={
                    'item': combined_lot_item['lot'],
                },
                dont_filter=True
            )
    
    def handle_lwin_response(self, response):
        item = response.meta['item']
        data = json.loads(response.text)

        lwinMatchingItem = LwinMatchingItem()
        lwinMatchingItem['lot_id'] = item['external_id']
        lwinMatchingItem['matched'] = data['matched']
        lwinMatchingItem['lwin'] = data['lwin_code']
        lwinMatchingItem['lwin_11'] = data['lwin_11_code'] if data['lwin_11_code'] else None
        lwinMatchingItem['match_score'] = data['match_score']
        lwinMatchingItem['match_item'] = json.dumps(data['match_item'])

        yield lwinMatchingItem
    
    def check_exists(self, id, type):
        if type == "auction":
            db_client = auctions_client
        elif type == "lot":
            db_client = lots_client
        
        result = db_client.get_by_external_id(id)
        return result is not None

