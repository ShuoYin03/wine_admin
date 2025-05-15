import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

class SothebysClient:
    def __init__(self):  
        self.api_url = "https://clientapi.prod.sothelabs.com/graphql"

    def auction_query(self, viking_id):
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
        
        return payload
    
    def lot_card_query(self, viking_id, lot_ids):
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
                    bidState {
                        ...BidStateFragment
                        ...TimedLotCountdownBidStateFragment
                    }
                }

                fragment BidStateFragment on BidState {
                    bidType: bidTypeV2 {
                        __typename
                    }
                    startingBid: startingBidV2 {
                        ...AmountFragment
                    }
                    sold {
                        ... on ResultVisible {
                            isSold
                            premiums {
                                finalPrice: finalPriceV2 {
                                    ...AmountFragment
                                }
                            }
                        }
                    }  
                }

                fragment TimedLotCountdownBidStateFragment on BidState {
                    closingTime
                }

                fragment AmountFragment on Amount {
                    currency
                    amount
                }
            """
        }

        return payload

    def extract_algolia_api_key(self, html):
        soup = BeautifulSoup(html, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
        algolia_api_key = json.loads(script_tag.string)['props']['pageProps']['algoliaSearchKey']

        return algolia_api_key

    def algolia_api(self, auction_id, api_key, page):
        url = "https://kar1ueupjd-dsn.algolia.net/1/indexes/prod_lots/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)%3B%20Browser"

        headers = {
            "accept-encoding": "gzip, deflate",
            "accept": "*/*",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7",
            "connection": "keep-alive",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.sothebys.com",
            "referer": "https://www.sothebys.com/",
            "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "x-algolia-api-key": api_key,
            "x-algolia-application-id": "KAR1UEUPJD",
        }

        payload = {
            "query": "",
            "filters": f"auctionId:'{auction_id}' AND objectTypes:'All' AND NOT isHidden:true AND NOT restrictedInCountries:'GB'",
            "facetFilters": [["withdrawn:false"], []],
            "hitsPerPage": 48,
            "page": page,
            "facets": ["*"],
            "numericFilters": [],
        }

        return url, headers, payload
    
