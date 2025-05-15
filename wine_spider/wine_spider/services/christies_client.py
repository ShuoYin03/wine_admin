from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

class ChristiesClient:
    def __init__(self):  
        self.api_url = "https://clientapi.prod.sothelabs.com/graphql"

    def lots_query(self, action, sale_id, filterids=None, page=1):
        url = f"https://onlineonly.christies.com/sale/searchLots"

        params = {
            "action": action,
            "language": "en",
            "page": page,
            "saleid": sale_id,
            "sid": "",
            "sortby": "LotNumber",
            "loadall": "true"
        }

        if filterids:
            params["filterids"] = "|" + filterids + "|"

        # if action == "paging":
        #     params["loadall"] = "true"

        return f"{url}?{urlencode(params)}"
    
    def saved_lots_query(self, action, sale_id, sale_number, filterids=None, page=1):
        url = "https://www.christies.com/api/discoverywebsite/auctionpages/lotsearch"
        
        params = {
            "action": action,
            "geocountrycode": "GB",
            "language": "en",
            "page": page,
            "saleid": sale_id,
            "salenumber": sale_number,
            "saletype": "Sale",
            "sortby": "lotnumber",
            "loadall": "true"
        }

        if filterids:
            params["filterids"] = "|" + filterids + "|"
        
        if action == "paging":
            params["loadall"] = "true"

        return f"{url}?{urlencode(params)}"