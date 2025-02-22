import os
import json
import time
import scrapy
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from wine_spider.helpers.date_parser import parse_quarter
from wine_spider.items import AuctionItem, AuctionSalesItem, LotItem
from wine_spider.helpers.continent_parser import find_continent
from wine_spider.helpers.volumn_parser import parse_volumn, parse_unit
from wine_spider.website_clients.sothebys_client import SothebysClient
from wine_spider.spiders.querys.sothebys import get_lot_id_query, get_lot_description_query

load_dotenv()

ALGOLIA_API_KEY = os.getenv('ALGOLIA_API_KEY')
ALGOLIA_APPLICATION_ID = os.getenv('ALGOLIA_APPLICATION_ID')

class SothebysSpider(scrapy.Spider):
    name = "sothebys_spider"
    allowed_domains = [
        "www.sothebys.com", 
        "clientapi.prod.sothelabs.com",
        "kar1ueupjd-2.algolianet.com",
        "algolia.net"
    ]
    start_urls = ["https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q="]

    def __init__(self, *args, **kwargs):
        super(SothebysSpider, self).__init__(*args, **kwargs)
        self.client = SothebysClient()

    def parse(self, response):
        total_pages = int(response.css('li.SearchModule-pageCounts span[data-page-count]::text').get())
        base_url = "https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&q=&p={}"
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
        for viking_id, url in data:
            payload = self.client.auction_query(viking_id)
            
            yield scrapy.Request(
                url=self.client.api_url,
                method='POST',
                body=json.dumps(payload),
                callback=self.parse_auction_api_response,
            )

            lots = []
            lot_ids = []
            response = self.client.go_to(url)
            algolia_api_key = self.client.extract_algolia_api_key(response)
            algolia_response = self.client.algolia_api(viking_id, algolia_api_key, 0)
            success_lot = parse_lots_page(response, algolia_response)
            lots.extend(success_lot)
            try:
                close = self.client.locate("#io01")
                close.click()
            except Exception:
                pass

            soup = BeautifulSoup(response, "html.parser")
            pagination = soup.select(".pagination-module_pagination__TRr2-")
            page_count = int(pagination[0].find_all("li")[-2].text) + 1
            
            for page in range(2, page_count):
                pagination_button = self.client.locate(f'li >> button[aria-label="Go to page {page}."]')
                pagination_button.scroll_into_view_if_needed()
                pagination_button.click()
                time.sleep(2.5)
                response = self.client.page.content()
                
                algolia_response = self.client.algolia_api(viking_id, algolia_api_key, page - 1)
                success_lot = parse_lots_page(response, algolia_response)
                lots.extend(success_lot)

            auction_sales_item = AuctionSalesItem()
            sold = 0
            total_low_estimate = 0
            total_high_estimate = 0
            total_sales = 0
            volumn_sold = 0
            top_lot = None
            top_lot_price = None
            current_cellar = None
            single_cellar = True

            for lot in lots:
                self.logger.info(lot)
                sold += 1 if lot['sold'] else 0
                total_low_estimate += lot['low_estimate']
                total_high_estimate += lot['high_estimate']
                total_sales += lot['end_price'] if lot['sold'] else 0
                try:
                    volumn_sold += parse_volumn(lot['unit'], lot['bottle_size'], lot['wine_name']) if lot['sold'] else 0
                except Exception:
                    lot['success'] = False
                if lot['sold'] and (not top_lot or lot['end_price'] > top_lot_price):
                    top_lot = lot['id']
                    top_lot_price = lot['end_price']
                if not current_cellar:
                    current_cellar = lot['lot_producer']
                elif current_cellar != lot['lot_producer']:
                    single_cellar = False
                lot_ids.append(lot['id'])
            
            payload = self.client.lot_card_query(viking_id, lot_ids)

            yield scrapy.Request(
                url=self.client.api_url,
                method='POST',
                body=json.dumps(payload),
                callback=self.parse_lot_api_response,
                meta={
                    "lots": lots
                },
            )

            auction_sales_item['id'] = viking_id
            auction_sales_item['lots'] = len(lots)
            auction_sales_item['sold'] = sold
            auction_sales_item['currency'] = lots[0]['original_currency']
            auction_sales_item['total_low_estimate'] = total_low_estimate
            auction_sales_item['total_high_estimate'] = total_high_estimate
            auction_sales_item['total_sales'] = total_sales
            auction_sales_item['volumn_sold'] = volumn_sold
            auction_sales_item['value_sold'] = total_sales
            auction_sales_item['top_lot'] = top_lot
            auction_sales_item['sale_type'] = "PAST"
            auction_sales_item['single_cellar'] = single_cellar
            auction_sales_item['ex_ch'] = False

            yield auction_sales_item

    def parse_auction_api_response(self, response):
        try:
            data = json.loads(response.text)['data']['auction']
            auction_item = AuctionItem()
            auction_item['id'] = data['id']
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
    
    def parse_lot_api_response(self, response):
        data = json.loads(response.text)['data']['auction']['lot_ids']
        data_dict = {item['lotId']: item['bidState']['startingBid']['amount'] for item in data}
        lots = response.meta.get("lots")
        for lot in lots:
            lot['start_price'] = data_dict[lot['id']]
            yield lot

def parse_lots_page(html, api_response):
    lots = []
    soup = BeautifulSoup(html, "html.parser")
    data = api_response['hits']
    for item in data:
        lot = LotItem()
        try:
            lot['id'] = item['objectID']
            lot['auction_id'] = item['auctionId']
            lot['lot_producer'] = item["Winery"][0] if "Winery" in item else item["Distillery"][0] if "Distillery" in item else None
            lot['wine_name'] = item['title']
            lot['vintage'] = item['Vintage'][0] if 'Vintage' in item and item['Vintage'] else item['age'][0] if 'age' in item else None
            lot['bottle_size'] = item['Spirit Bottle Size'][0] if 'Spirit Bottle Size' in item else None
            lot['original_currency'] = item['currency']
            lot['low_estimate'] = item['lowEstimate']
            lot['high_estimate'] = item['highEstimate']
            lot['region'] = item['Region'][0] if 'Region' in item else None
            lot['country'] = item.get('Country', None)
            lot['success'] = True

            try:
                price = soup.find("div", id="lot-list").find("div", attrs={"data-testid": item['objectID']}).find("p", attrs={"data-testid": "currentBid"}).text
                price = int(price.split(" ")[0].replace(",", ""))
                lot['end_price'] = price
                lot['sold'] = True
            except Exception as e:
                lot['end_price'] = None
                lot['sold'] = False

            lot['unit'], lot['unit_format'] = parse_unit(item['title']) if 'Spirit Bottle Size' in item else (None, None)
            
        except Exception as e:
            lot['unit'], lot['unit_format'] = None, None
            lot['success'] = False

        lots.append(lot)
    return lots


