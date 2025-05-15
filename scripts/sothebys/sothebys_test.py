import requests
url = "https://clientapi.prod.sothelabs.com/graphql"
payload = {
    "operationName": "LotCardsQuery",
    "variables": {
        "id": "b6b7eb49-c84a-49a5-8389-1f66d13823597",
        "lotIds": ['1430aaab-21cb-4bd3-8e3e-77ec32e6ccd2', '2ac8a32c-8d1d-4010-b85a-9c540d05c675', 'c365a194-106f-412a-9a5d-52a682d68c5f'],
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

response = requests.post(url, json=payload)
print(response.json())