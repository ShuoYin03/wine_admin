import requests
import json

payload = {
    "operationName": "AuctionQuery",
    "variables": {
        "id": "82bab296-9e0d-446b-9e70-dfc2606256c4",
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