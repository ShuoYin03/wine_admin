import re
import os
import json
import scrapy
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from wine_spider.helpers.date_parser import parse_quarter
from wine_spider.items import AuctionItem, AuctionSalesItem
from wine_spider.helpers.captcha_parser import CaptchaParser
from wine_spider.helpers.continent_parser import find_continent
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
            
            # yield scrapy.Request(
            #     url=auction_api_url,
            #     method='POST',
            #     body=json.dumps(payload),
            #     callback=self.parse_auction_api_response,
            # )

            yield scrapy.Request(
                url=self.client.api_url,
                method='GET',
                callback=self.get_all_lot_ids,
                meta={"viking_id": viking_id},
            )

    def get_all_lot_ids(self, response):
        viking_id = response.meta.get("viking_id")
        lot_id_urls = response.css(".css-davmek::attr(src)").getall()
        lot_id_url = lot_id_urls[0]
        lot_id = re.search(r"/lot/([a-f0-9\-]+)/", lot_id_url).group(1)
        
        payload = {
            "operationName": "LotQuery",
            "variables": {
                "auctionId": viking_id,
                "countryOfOrigin": "GB",
                "id": lot_id,
                "language": "ENGLISH"
            },
            "query": get_lot_id_query()
        }

        yield scrapy.Request(
            url=self.client.api_url,
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(payload),
            callback=self.query_lots,
            meta={
                "viking_id": viking_id
            },
        )

    def query_lots(self, response):
        viking_id = response.meta.get("viking_id")

        base_url = "https://www.sothebys.com/en/buy/auction/2025"
        lot_paths = [os.path.join(base_url, lot["slug"]["lotSlug"], lot["slug"]["auctionSlug"]["name"]) for lot in json.loads(response.text)['data']['lot']['auction']['lotCards']]
        lot_ids = [lot['lotId'] for lot in json.loads(response.text)['data']['lot']['auction']['lotCards']]

        lot_data = []
        for lot_path in lot_paths[:10]:
            response = self.client.go_to(lot_path)
            soup = BeautifulSoup(response, "html.parser")
            lot_title = soup.find("h1", class_="headline-module_headline24Regular__FNS1U css-g38yz4")
            lot_auction_house = soup.find("div", class_="css-1aw519d").find("p").find("em", recursive=False)
            price = soup.find("p", class_="label-module_label16Medium__Z4VRX css-xrn2do") 
            lot_data.append({
                "title": lot_title.text,
                "auction_house": lot_auction_house.text,
                "price": price.text
            })

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
        with open("response.json", "w") as f:
            json.dump(response.json(), f, indent=4)

        with open("lots_data.txt", "r") as f:
            f.writelines(json.dumps(response.meta.get("lot_data")))
        # viking_id = response.meta.get("viking_id")

        # lot_sales_data = {
        #     "total_sold": 0,
        #     "total_low_estimate": 0,
        #     "total_high_estimate": 0,
        #     "total_sales": 0
        # }

        # for lot in response.json()['data']['auction']['lot_ids']:
        #     lot_sales_data["total_low_estimate"] += lot['estimateV2']['lowEstimate']['amount']
        #     lot_sales_data["total_high_estimate"] += lot['estimateV2']['highEstimate']['amount']
        #     lot_sales_data["total_sales"] += lot['bidState']['sold']['premiums']['finalPrice']['amount'] if lot['bidState']['sold']['isSold'] else 0

        # auction_sales_item = AuctionSalesItem()
        # auction_sales_item['id'] = viking_id['id']
        # auction_sales_item['lots'] = len(response.json()['data']['auction']['lot_ids'])
        # auction_sales_item['sold'] = lot_sales_data["total_sold"]
        # auction_sales_item['total_low_estimate'] = find_continent(data['location']['name'])
        # auction_sales_item['total_high_estimate'] = data['dates']['acceptsBids']
        # auction_sales_item['total_sales'] = data['dates']['closed']
        # auction_sales_item['volumn_sold'] = int(data['dates']['closed'].split("-")[0])
        # auction_sales_item['value_sold'] = parse_quarter(int(data['dates']['closed'].split("-")[1]))
        # auction_sales_item['top_lot'] = "PAST"
        # auction_sales_item['sale_type'] = "PAST"
        # auction_sales_item['exch'] = "PAST"

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
            # total_lots = len(response.json()['data']['auction']['lot_ids'])
            # total_sold = 0
            # total_low_estimate = 0
            # total_high_estimate = 0
            # for lot in response.json()['data']['auction']['lot_ids']:
            #     total_sold += 1 if lot['bidState']['sold']['isSold'] else 0
            #     total_low_estimate += lot['estimateV2']['lowEstimate']['amount']
            #     total_high_estimate += lot['estimateV2']['highEstimate']['amount']

            #     auction_sales_item = AuctionSalesItem()
            #     auction_sales_item['lot_id'] = lot['lotId']
            #     auction_sales_item['title'] = lot['title']
            #     auction_sales_item['lot_number'] = lot['lotNumber']['lotNumber']
            #     auction_sales_item['starting_bid'] = lot['bidState']['startingBid']['amount']
            #     auction_sales_item['sold'] = lot['bidState']['sold']['isSold']
            #     auction_sales_item['final_price'] = lot['bidState']['sold']['premiums']['finalPrice']['amount'] if lot['bidState']['sold']['isSold'] else None
            #     auction_sales_item['low_estimate'] = lot['estimateV2']['lowEstimate']['amount']
            #     auction_sales_item['high_estimate'] = lot['estimateV2']['highEstimate']['amount']
            #     auction_sales_item['currency'] = lot['estimateV2']['highEstimate']['currency']
            #     auction_sales_item['total_lots'] = total_lots
            #     auction_sales_item['total_sold'] = total_sold       
            #     auction_sales_item['total_low_estimate'] = total_low_estimate
            #     auction_sales_item['total_high_estimate'] = total_high_estimate                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             

            #     yield auction_sales_item
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON for Viking IDs")


