import requests
import json

payload = {
    "operationName": "AuctionQuery",
    "variables": {
        "id": "3b8bf8c7-7a20-47df-b25e-d5f0efb29539",
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

response = requests.post("https://clientapi.prod.sothelabs.com/graphql", json=payload)
data = response.json()
print(data)