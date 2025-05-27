class ZachysClient:
    def __init__(self, base_url="https://bid.zachys.com/auctions"):
        self.base_url = base_url

    def get_auction_url(self, page=1):
        """
        Constructs the URL for fetching auctions for a specific page.
        """
        return f"{self.base_url}?page={page}&status=1"
    
    def get_lots_url(self, auction_id, auction_seo_name, page=1):
        """
        Constructs the URL for fetching lots of a specific auction.
        """
        return f"{self.base_url}/catalog/id/{auction_id}/{auction_seo_name}?items=100&page={page}"