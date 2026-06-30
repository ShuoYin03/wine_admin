from scrapy.utils.reactor import install_reactor
install_reactor('twisted.internet.asyncioreactor.AsyncioSelectorReactor')

import os
import json
import scrapy
import dotenv
import pandas as pd
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.spiders.base_auction_spider import should_skip_existing_auction_record
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
from wine_spider.helpers import find_continent, region_to_country, parse_quarter, parse_volume_and_unit_from_title, parse_year_from_title, match_lot_info, build_lot_external_id

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH", "False").lower() == "true"
TARGET_AUCTION_IDS = {
    auction_id.strip()
    for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
    if auction_id.strip()
}
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
        "LOG_FILE": build_spider_log_file("sothebys.log"),
        # "JOBDIR": "wine_spider/crawl_state/sothebys",
        "SOTHEBYS_STATE_PATH": "wine_spider/login_state/sothebys_cookies.json",
        "SOTHEBYS_STATE_EXPIRE_DAYS" : 10,
        "SOTHEBYS_LOGIN_SCRIPT": "wine_spider/helpers/sothebys/login.py",
        "PLAYWRIGHT_CONTEXTS": {
            "sothebys": {
                "storage_state": "wine_spider/login_state/sothebys_cookies.json"
            }
        },
        "DOWNLOADER_MIDDLEWARES": {
            'wine_spider.middlewares.sothebys_login_middleware.SothebysLoginMiddleware': 100,
        }
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
        for page in range(1, total_pages + 1):
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
            if TARGET_AUCTION_IDS and viking_id not in TARGET_AUCTION_IDS:
                self.logger.debug(f"Auction {viking_id} is not in BACKFILL_AUCTION_IDS. Skipping...")
                continue

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

            yield self.build_algolia_key_request(viking_id, url=url)

    async def after_auth(self, response):
        url = response.meta.get("url")
        viking_id = response.meta.get("viking_id")
        page = response.meta["playwright_page"]
        token = None

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            html = await page.content()
            algolia_api_key = self.client.extract_algolia_api_key(html)

            if algolia_api_key:
                yield self.build_algolia_request(viking_id, algolia_api_key, 0, token)
            else:
                self.logger.error(f"Failed to extract Algolia key from fallback page for auction {viking_id}")

        except Exception as e:
            self.logger.error(f"Error in after_auth: {e}")
        finally:
            if not page.is_closed():
                await page.close()

    def build_algolia_key_request(self, viking_id, url=None, token=None):
        return scrapy.Request(
            url=self.client.api_url,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": "https://www.sothebys.com",
                "Referer": "https://www.sothebys.com/",
            },
            body=json.dumps(self.client.algolia_search_key_query(viking_id)),
            callback=self.parse_algolia_key_response,
            priority=10,
            meta={
                "viking_id": viking_id,
                "token": token,
                "url": url,
            },
            dont_filter=True,
        )

    def build_playwright_key_request(self, viking_id, url):
        return scrapy.Request(
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
                "url": url,
            },
        )

    def parse_algolia_key_response(self, response):
        viking_id = response.meta.get("viking_id")
        token = response.meta.get("token")
        url = response.meta.get("url")
        data = response.json()
        algolia_api_key = (
            (data.get("data") or {})
            .get("algoliaSearchKey", {})
            .get("key")
        )

        if not algolia_api_key:
            self.logger.error(f"Failed to fetch Algolia API key for auction {viking_id}: {data}")
            if url:
                yield self.build_playwright_key_request(viking_id, url)
            return

        yield self.build_algolia_request(viking_id, algolia_api_key, 0, token)

    def build_algolia_request(self, viking_id, algolia_api_key, page, token=None):
        algolia_url, algolia_headers, algolia_payload = self.client.algolia_api(
            viking_id,
            algolia_api_key,
            page,
        )

        return scrapy.Request(
            url=algolia_url,
            method="POST",
            headers=algolia_headers,
            body=json.dumps(algolia_payload),
            callback=self.parse_lots_page,
            meta={
                "viking_id": viking_id,
                "token": token,
                "algolia_api_key": algolia_api_key,
                "page": page,
            },
            dont_filter=True,
        )

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
        response_data = response.json()
        data = response_data.get("hits", [])
        page = response.meta.get("page", 0)
        algolia_api_key = response.meta.get("algolia_api_key")

        if page == 0 and algolia_api_key:
            for next_page in range(1, response_data.get("nbPages", 1)):
                yield self.build_algolia_request(viking_id, algolia_api_key, next_page, token)

        lots = []
        lot_detail_items = []
        combined_lot_items = []
        lot_card_ids_by_external_id = {}

        for item in data:
            source_lot_id = item['objectID']
            lot_external_id = build_lot_external_id(item['auctionId'], source_lot_id)
            lot = LotItem()
            if not FULL_FETCH and self.check_exists(lot_external_id, "lot"):
                self.logger.info(f"Lot {lot_external_id} exists, Skipping...")
                continue

            lot['external_id'] = lot_external_id
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
                self.logger.error(f"Failed to parse lot {lot_external_id}: {e}")

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
            lot_card_ids_by_external_id[lot_external_id] = source_lot_id
        
        lot_ids = [lot_card_ids_by_external_id[lot['external_id']] for lot in lots]
        if not lot_ids:
            return

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
                "lot_card_ids_by_external_id": lot_card_ids_by_external_id,
            },
        )   

    def parse_lot_api_response(self, response):
        lots = response.meta.get("lots")
        lot_items = response.meta.get("lot_items")
        combined_lot_items = response.meta.get("combined_lot_items")
        lot_card_ids_by_external_id = response.meta.get("lot_card_ids_by_external_id") or {}
        try:
            data = response.json()['data']['auction']['lot_ids']
        except Exception as e:
            self.logger.error(f"Failed to parse Sotheby's lot card response: {e}")
            for lot in lots:
                yield lot
            for lot_item in lot_items:
                yield lot_item
            return

        data_dict = {}
        for item in data:
            lot_id = item.get("lotId")
            if not lot_id:
                continue
            data_dict[lot_id] = self.parse_lot_card_bid_state(item)
        
        for lot in lots:
            lot_card = data_dict.get(lot_card_ids_by_external_id.get(lot['external_id']))
            if not lot_card:
                yield lot
                continue

            if len(lot_card) == 4:
                lot['start_price'], lot['end_price'], lot['sold'], lot['sold_date'] = lot_card
            else:
                lot['start_price'], lot['sold'], lot['sold_date'] = lot_card

            yield lot

        for lot_item in lot_items:
            yield lot_item

        for combined_lot_item in combined_lot_items:
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

    def parse_lot_card_bid_state(self, item):
        bid_state = item.get("bidState") or {}
        starting_bid = (bid_state.get("startingBid") or {}).get("amount")
        sold_state = bid_state.get("sold") or {}
        closing_time = bid_state.get("closingTime")
        is_sold = bool(sold_state.get("isSold"))

        if is_sold:
            final_price = (
                ((sold_state.get("premiums") or {}).get("finalPrice") or {})
                .get("amount")
            )
            return starting_bid, final_price, True, closing_time

        return starting_bid, False, closing_time
    
    def handle_lwin_response(self, response):
        item = response.meta['item']
        payload = json.loads(response.text)
        data = payload.get("data", payload)

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
            return should_skip_existing_auction_record(
                id,
                auctions_client,
                lot_client=lots_client,
                full_fetch=FULL_FETCH,
                logger=self.logger,
            )
        elif type == "lot":
            db_client = lots_client
            result = db_client.get_by_external_id(id)
            return result is not None

        return False

