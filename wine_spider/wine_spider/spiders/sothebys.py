import os
import json
import time
import scrapy
import pandas as pd
from bs4 import BeautifulSoup
from wine_spider.helpers import parse_quarter
from wine_spider.helpers import find_continent
from wine_spider.items import AuctionItem, LotItem
from wine_spider.website_clients.sothebys_client import SothebysClient
from wine_spider.helpers import parse_volumn_and_unit_from_title, parse_year_from_title, match_lot_info

class SothebysSpider(scrapy.Spider):
    name = "sothebys_spider"
    allowed_domains = [
        "www.sothebys.com", 
        "clientapi.prod.sothelabs.com",
        "kar1ueupjd-2.algolianet.com",
        "algolia.net"
    ]
    start_urls = ["https://www.sothebys.com/en/results?from=&to=&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q="]

    def __init__(self, *args, **kwargs):
        super(SothebysSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))
        self.base_url = "https://www.sothebys.com"
        self.cookies_path = "wine_spider/login_state/sothebys_cookies.json"
        
        if not os.path.exists(self.cookies_path):
            self.client = SothebysClient(False)
        else:
            self.client = SothebysClient(True)

        with open(self.cookies_path, 'r', encoding='utf-8') as f:
            cookie_data = json.load(f)
        self.cookies = []
        for cookie in cookie_data.get("cookies", []):
            self.cookies.append({
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie["domain"],
                "path": cookie["path"],
                "expires": cookie.get("expires"),
                "secure": cookie.get("secure")
            })

    def parse(self, response):
        total_pages = int(response.css('li.SearchModule-pageCounts span[data-page-count]::text').get())
        self.logger.info(f"Crawling Total pages: {total_pages}")
        base_url = "https://www.sothebys.com/en/results?from=&to=&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q=&p={}"
        for page in range(1, 2):
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

        for viking_id, url in data[1:4]:
            payload = self.client.auction_query(viking_id)
            
            yield scrapy.Request(
                url=self.client.api_url,
                method='POST',
                body=json.dumps(payload),
                callback=self.parse_auction_api_response,
            )

            response, token = self.client.get_authorisation_token_and_response(url)
            try:
                soup = BeautifulSoup(response, "html.parser")
                pagination = soup.select(".pagination-module_pagination__TRr2-")
                page_count = int(pagination[0].find_all("li")[-2].text) + 1
            except Exception:
                page_count = 1
                print("Unable to find page number for the following url:", url)
            
            algolia_api_key = self.client.extract_algolia_api_key(response)

            for page in range(0, page_count):
                algolia_url, algolia_headers, algolia_payload = self.client.algolia_api(viking_id, algolia_api_key, page)
            
                yield scrapy.Request(
                    url=algolia_url,
                    method='POST',
                    headers=algolia_headers,
                    body=json.dumps(algolia_payload),
                    callback=self.parse_lots_page,
                    meta={
                        "viking_id": viking_id,
                        "token": token
                    }
                )

    def parse_auction_api_response(self, response):
        try:
            data = json.loads(response.text)['data']['auction']
            auction_item = AuctionItem()
            auction_item['id'] = data['auctionId']
            auction_item['auction_title'] = data['title']
            auction_item['auction_house'] = "Sotheby's"
            auction_item['city'] = data['location']['name']
            auction_item['continent'] = find_continent(data['location']['name'])
            auction_item['start_date'] = data['dates']['acceptsBids']
            auction_item['end_date'] = data['dates']['closed']
            auction_item['year'] = int(data['dates']['closed'].split("-")[0])
            auction_item['quarter'] = parse_quarter(int(data['dates']['closed'].split("-")[1]))
            auction_item['auction_type'] = "PAST"
            
            yield auction_item
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON for UUIDs")


    def parse_lots_page(self, response):
        viking_id = response.meta.get("viking_id")
        token = response.meta.get("token")
        self.logger.info(f"token: {token}")
        data = response.json()['hits']

        lots = []
        for item in data:
            lot = LotItem()
            try:
                lot['id'] = item['objectID']
                lot['auction_id'] = item['auctionId']
                lot['lot_producer'] = item["Winery"] if "Winery" in item else item["Distillery"] if "Distillery" in item else None
                lot['wine_name'] = item['title']
                lot['vintage'] = item['Vintage'] if 'Vintage' in item else item['age'] if 'age' in item else None
                lot['unit_format'] = item['Spirit Bottle Size'] if 'Spirit Bottle Size' in item else None
                lot['original_currency'] = item['currency']
                lot['low_estimate'] = item['lowEstimate']
                lot['high_estimate'] = item['highEstimate']
                lot['region'] = item['Region'][0] if 'Region' in item else None
                lot['country'] = item['Country'][0] if 'Country' in item else None
                lot['success'] = True
                lot['url'] = f"{self.base_url}{item['slug']}"

                if not lot['vintage']:
                    lot['vintage'] = [str(parse_year_from_title(item['title']))] if parse_year_from_title(item['title']) else None

                lot['volumn'], lot['unit'] = parse_volumn_and_unit_from_title(item['title'])
                
                if not lot['lot_producer'] or not lot['region'] or not lot['country']:
                    lot_info = match_lot_info(lot['wine_name'], self.lwin_df)
                    lot['lot_producer'] = [lot_info[0]] if not lot['lot_producer'] else lot['lot_producer']
                    lot['region'] = lot_info[1] if not lot['region'] else lot['region']
                    lot['country'] = lot_info[2] if not lot['country'] else lot['country']
                
            except Exception as e:
                self.logger.error(f"Failed to parse lot {item['objectID']}: {e}")
                lot['success'] = False

            lots.append(lot)
        
        lot_ids = [lot['id'] for lot in lots]
        payload = self.client.lot_card_query(viking_id, lot_ids)

        hearders = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        yield scrapy.Request(
            url=self.client.api_url,
            method='POST',
            cookies=self.cookies,
            headers=hearders,
            body=json.dumps(payload),
            callback=self.parse_lot_api_response,
            meta={
                "lots": lots
            },
        )   


    def parse_lot_api_response(self, response):
        lots = response.meta.get("lots")
        data = json.loads(response.text)['data']['auction']['lot_ids']
        try:
            data_dict = {
                item['lotId']: (
                    (item['bidState']['startingBid']['amount'], item['bidState']['sold']['premiums']['finalPrice']['amount'], item['bidState']['sold']['isSold'])
                    if item['bidState']['sold']['isSold']
                    else (item['bidState']['startingBid']['amount'], item['bidState']['sold']['isSold'])
                )
                for item in data
            }

            for lot in lots:
                if len(data_dict.get(lot['id'])) == 3:
                    lot['start_price'], lot['end_price'], lot['sold'] = data_dict[lot['id']]
                else:
                    lot['start_price'], lot['sold'] = data_dict[lot['id']]
                yield lot
                
        except Exception as e:
            self.logger.error(f"Failed to parse lot data: {e}")
            self.logger.debug(f"Response: {response.text}")
            for lot in lots:
                lot['success'] = False
                yield lot


