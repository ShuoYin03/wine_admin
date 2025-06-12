class BagheraClient:
    def __init__(self):
        pass

    def get_auction_url(self, base_url):
        """
        Constructs the URL for fetching auctions for a specific page.
        """
        return f"{base_url}?search=1&order_dir=&per_page=1000&estimation_min=&mot_cle="
    
    def get_filtered_auction_url(self, base_url, filter_name, data):
        """
        Constructs the URL for fetching filtered lots based on the provided filter name and labels.
        """
        return f"{base_url}?search=1&order_dir=&per_page=1000&{filter_name}={data}&estimation_min=&mot_cle"