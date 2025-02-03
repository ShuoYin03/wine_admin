import scrapy
import json
import requests 
from dotenv import load_dotenv
import os
from wine_spider.items import AuctionItem, AuctionSalesItem
from wine_spider.helpers.continent_parser import find_continent

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
    start_urls = ["https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&q="]

    def parse(self, response):
        total_pages = int(response.css('li.SearchModule-pageCounts span[data-page-count]::text').get())

        base_url = "https://www.sothebys.com/en/results?from=&to=&f2=0000017e-b9db-d1d4-a9fe-bdfb5bbc0000&q=&p={}"
        for page in range(1, 2):
            url = base_url.format(page)
            yield scrapy.Request(
                url=url, 
                callback=self.parse_uuids
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
        
        auction_api_url = "https://clientapi.prod.sothelabs.com/graphql"
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
            #     meta={"viking_id": viking_id}
            # )

            yield scrapy.Request(
                url=url,
                method='GET',
                callback=self.query_lots,
                meta={"viking_id": viking_id}
            )

            return

    def query_lots(self, response):
        viking_id = response.meta.get("viking_id")
        lot_ids = response.css('div.css-16hfocp-LotItemListCard.row[data-testid]').getall()
        lot_api_url = "https://clientapi.prod.sothelabs.com/graphql"
        self.logger.debug(f"lot_ids: {lot_ids}")
        # payload = {
        #     "operationName": "LotCardsQuery",
        #     "variables": {
        #         "id": viking_id,
        #         "lotIds": [lot_ids],
        #         "language": "ENGLISH"
        #     },
        #     "query": """
        #         query LotCardsQuery($id: String!, $lotIds: [String!]!, $language: TranslationLanguage!) {
        #             auction(id: $id, language: $language) {
        #                 lotCards {
        #                     lotId
        #                     title
        #                     lotNumber {
        #                         lotNumber
        #                     }
        #                     bidState {
        #                         bidType {
        #                             __typename
        #                         }
        #                         sold {
        #                             isSold
        #                         }
        #                     }
        #                 }
        #             }
        #         }
        #     """
        # }

        # yield scrapy.Request(
        #     url=lot_api_url,
        #     method='POST',
        #     body=json.dumps(payload),
        #     callback=self.parse_lot_api_response
        # )

    def parse_auction_api_response(self, response):
        try:
            data = json.loads(response.text)['data']['auction']
            auction_item = AuctionItem(
                id=data['auctionId'],
                auction_title=data['title'],
                auction_house="Sotheby's",
                city=data['location']['name'],
                continent=find_continent(data['location']['name']),
                start_date=data['dates']['acceptsBids'],
                end_date=data['dates']['closed'],
                year=None,
                quarter=None,
                auction_type=None
            )
            yield auction_item
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON for UUIDs")
    
    def parse_lot_api_response(self, response):
        try:
            # data = json.loads(response.text)['data']['lot']
            # lot_item = AuctionSalesItem(
            #     id=data['id'],
            #     lot_number=data['lotNumber'],
            #     title=data['title'],
            #     description=data['description'],
            #     estimate=data['estimate'],
            #     currency=data['currency'],
            #     low_estimate=data['lowEstimate'],
            #     high_estimate=data['highEstimate'],
            #     sale_price=data['salePrice'],
            #     sold=data['sold'],
            #     image_urls=[image['url'] for image in data['images']],
            #     artist=data['artist']['name'],
            #     category=data['category']['name'],
            #     height=data['dimensions']['height'],
            #     width=data['dimensions']['width'],
            #     depth=data['dimensions']['depth']
            # )
            # yield lot_item
            data = json.loads(response.text)
            yield data
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON for Viking IDs")
        
    
