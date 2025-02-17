import re
import os
import json
import scrapy
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from wine_spider.helpers.date_parser import parse_quarter
from wine_spider.items import AuctionItem, AuctionSalesItem, LotItem
from wine_spider.helpers.continent_parser import find_continent
from wine_spider.helpers.volumn_parser import parse_volumn
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
        data = [(asset_data.get("vikingId"), asset_data.get("url")) for _, asset_data in data.items()][:1]
        for viking_id, url in data:
            payload = {
                "operationName": "AuctionQuery",
                "variables": {
                    "id": viking_id,
                    "language": "ENGLISH"
                },
                "query": """
                    query AuctionQuery($id: String!, $language: TranslationLanguage!) {
                        auction(id: $id, language: $language) {
                            id
                            auctionId
                            title
                            currency
                            location: locationV2 {
                                name
                            }
                            dates {
                                acceptsBids
                                closed    
                            }
                            sessions {
                                lotRange {
                                    fromLotNr
                                    toLotNr
                                }
                            }
                            state
                        }
                    }
                """
            }
            
            yield scrapy.Request(
                url=self.client.api_url,
                method='POST',
                body=json.dumps(payload),
                callback=self.parse_auction_api_response,
            )

            # yield scrapy.Request(
            #     url=url,
            #     method='GET',
            #     callback=self.get_all_lot_ids,
            #     meta={"viking_id": viking_id},
            # )

            lots = []
            response = self.client.go_to(url)
            lots.extend(parse_lots_page(response))

            soup = BeautifulSoup(response, "html.parser")
            pagination = soup.select(".pagination-module_pagination__TRr2-")
            page_count = pagination[0].find_all("li")[-2].text
            
            for page in range(2, page_count):
                pagination_button = self.client.locate(f'li >> button[aria-label="Go to page {page}."]')
                pagination_button.scroll_into_view_if_needed()
                pagination_button.click()
                response = self.client.page.content()
                lots.extend(parse_lots_page(response))

    def get_all_lot_ids(self, response):
        # viking_id = response.meta.get("viking_id")
        # lot_id_urls = response.css(".css-davmek::attr(src)").getall()
        # lot_id_url = lot_id_urls[0]
        # lot_id = re.search(r"/lot/([a-f0-9\-]+)/", lot_id_url).group(1)
        
        # payload = {
        #     "operationName": "LotQuery",
        #     "variables": {
        #         "auctionId": viking_id,
        #         "countryOfOrigin": "GB",
        #         "id": lot_id,
        #         "language": "ENGLISH"
        #     },
        #     "query": get_lot_id_query()
        # }

        # yield scrapy.Request(
        #     url=self.client.api_url,
        #     method='POST',
        #     headers={'Content-Type': 'application/json'},
        #     body=json.dumps(payload),
        #     callback=self.query_lots,
        #     meta={
        #         "viking_id": viking_id
        #     },
        # )
        pass

    def query_lots(self, response):
        viking_id = response.meta.get("viking_id")
        base_url = "https://www.sothebys.com/en/buy/auction"
        lot_paths = [os.path.join(base_url, lot['slug']['auctionSlug']['year'],  lot['slug']['auctionSlug']['name'], lot['slug']['lotSlug']) for lot in json.loads(response.text)['data']['lot']['auction']['lotCards']]
        lot_ids = [lot['lotId'] for lot in json.loads(response.text)['data']['lot']['auction']['lotCards']]

        lot_data = {}
        for lot_path in lot_paths[:10]:
            response = self.client.go_to(lot_path)
            soup = BeautifulSoup(response, "html.parser")
            
            lot_number = soup.find("div", attrs={"data-testid": "lotDropDown"}).find("p")
            lot_title = soup.find("h1", attrs={"data-cy": "lot-title", "data-testid": "lotTitle"})
            lot_auction_house = soup.find("div", attrs={"data-testid": "lotDetails"}).find("p", lambda tag: tag.find("em"))
            price = soup.find("div", attrs={"data-testid": "lotBidAmount"}).find_all("p")[1]
            lot_data[lot_number.text.split(" ")[-1]] = {
                "title": lot_title.text,
                "auction_house": lot_auction_house.text,
                "price": price.text
            }

        payload = {
            "operationName": "LotCardsQuery",
            "variables": {
                "id": viking_id,
                "lotIds": lot_ids,
                "language": "ENGLISH"
            },
            "query": """
                query LotCardsQuery($id: String!, $lotIds: [String!]!, $language: TranslationLanguage!) {
                    auction(id: $id, language: $language) {
                        lot_ids: lotCardsFromIds(ids: $lotIds) {
                            ...LotItemFragment
                        }
                    }
                }

                fragment LotItemFragment on LotCard {
                    lotId
                    title
                    lotNumber {
                        ... on VisibleLotNumber {
                            lotNumber
                        }
                    }
                    bidState {
                        ...BidStateFragment
                    }
                    estimateV2 {
                        ... on LowHighEstimateV2 {
                            highEstimate {
                                amount
                            }
                            lowEstimate {
                                amount
                            }
                        }
                    }
                }

                fragment BidStateFragment on BidState {
                    bidType: bidTypeV2 {
                        __typename
                    }
                    startingBid: startingBidV2 {
                        ...AmountFragment
                    }
                }

                fragment AmountFragment on Amount {
                    currency
                    amount
                }
            """
        }

        with open("lots_data.json", "w", encoding="utf-8") as f:
            json.dump(lot_data, f, indent=4)

        yield scrapy.Request(
            url=self.client.api_url,
            method='POST',
            body=json.dumps(payload),
            callback=self.query_lot_description,
            meta={
                "viking_id": viking_id,
                "lot_data": lot_data
            },
        )

    def query_lot_description(self, response):
        viking_id = response.meta.get("viking_id")
        lot_data = response.meta.get("lot_data")

        lot_sales_data = {
            "total_sold": 0,
            "total_low_estimate": 0,
            "total_high_estimate": 0,
            "total_sales": 0,
            "volumn_sold": 0,
        }

        top_lot = None
        top_lot_price = None
        current_cellar = None
        single_cellar = True
        for lot in response.json()['data']['auction']['lot_ids']:
            lot_sales_data["total_low_estimate"] += lot['estimateV2']['lowEstimate']['amount']
            lot_sales_data["total_high_estimate"] += lot['estimateV2']['highEstimate']['amount']
            lot_sales_data["total_sales"] += lot['bidState']['sold']['premiums']['finalPrice']['amount'] if lot['bidState']['sold']['isSold'] else 0
            lot_sales_data["volumn_sold"] += parse_volumn(lot["title"])
            current_sold = lot_data[lot["lotId"]]["price"].split(" ")[0]
            lot_sales_data["total_sold"] += current_sold

            if not top_lot or current_sold > top_lot_price:
                top_lot = lot["lotId"]
                top_lot_price = current_sold
            
            if not current_cellar:
                current_cellar = lot_data[lot["lotId"]]["auction_house"]
            elif current_cellar != lot_data[lot["lotId"]]["auction_house"]: 
                single_cellar = False

        auction_sales_item = AuctionSalesItem()
        auction_sales_item['id'] = viking_id
        auction_sales_item['lots'] = len(response.json()['data']['auction']['lot_ids'])
        auction_sales_item['sold'] = lot_sales_data["total_sold"]
        auction_sales_item['total_low_estimate'] = lot_sales_data["total_low_estimate"]
        auction_sales_item['total_high_estimate'] = lot_sales_data["total_high_estimate"]
        auction_sales_item['total_sales'] = lot_sales_data["total_sales"]
        auction_sales_item['volumn_sold'] = lot_sales_data["volumn_sold"]
        auction_sales_item['value_sold'] = lot_sales_data["total_sales"]
        auction_sales_item['top_lot'] = top_lot
        auction_sales_item['sale_type'] = "PAST"
        auction_sales_item['single_cellar'] = single_cellar
        auction_sales_item['exch'] = None

        # lots = [(lot["lotId"], lot) for lot in json.loads(response.text)['data']['auction']['lot_ids']]
        # lot_api_url = "https://clientapi.prod.sothelabs.com/graphql"
        
        # for lot_id, lot in lots:
        #     payload = {
        #         "operationName": "LotQuery",
        #         "variables": {
        #             "auctionId": viking_id,
        #             "countryOfOrigin": "GB",
        #             "id": lot_id,
        #             "language": "ENGLISH"
        #         },
        #         "query": get_lot_description_query()
        #     }

        #     yield scrapy.Request(
        #         url=self.client.api_url,
        #         method='POST',
        #         headers={'Content-Type': 'application/json'},
        #         body=json.dumps(payload),
        #         callback=self.parse_lot_api_response,
        #         meta={
        #             "viking_id": viking_id,
        #             "lot_id": lot,
        #             "lot_data": lot_data
        #         },
        #         cookies=self.cookies
        #     )

        #     return

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
        try:
            pass

        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON for Viking IDs")


def parse_lots_page(html):
    lots = []
    soup = BeautifulSoup(html, "html.parser")
    script_tag = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
    data = json.loads(script_tag.string)['props']['pageProps']['algoliaJson']['hits']

    for item in data:
        lot = LotItem()
        lot['id'] = item['objectID']
        lot['auction_id'] = item['auctionId']
        lot['lot_producer'] = item['Winery']
        lot['wine_name'] = item['title']
        lot['vintage'] = item['Vintage']
        lot['unit_format'] = item['Spirit Bottle Size']
        lot['unit'] = item['Spirit Bottle Size']
        lot['currency'] = item['currency']
        lot['low_estimate'] = item['lowEstimate']
        lot['high_estimate'] = item['highEstimate']
        lot['region'] = item['Region']
        lot['country'] = item['Country']
        lots.append(lot)
    
    return lots
        


