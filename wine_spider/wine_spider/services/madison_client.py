class MadisonClient:
    def __init__(self):
        pass

    def get_auction_api_url(self, page=1, size=200):
        return f"https://api.madison-auction.com/v1/auction/list?page={page}&size={size}"