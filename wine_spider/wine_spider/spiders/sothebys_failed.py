import scrapy
from database import DatabaseClient

class SothebysSpider(scrapy.Spider):
    name = "sothebys_failed_spider"
    allowed_domains = [
        "www.sothebys.com", 
        "clientapi.prod.sothelabs.com",
        "kar1ueupjd-2.algolianet.com",
        "algolia.net"
    ]
    start_urls = ["https://www.sothebys.com/en/results?from=&to=&f2=00000164-609a-d1db-a5e6-e9fffcc80000&q="]

    def __init__(self, *args, **kwargs):
        super(SothebysSpider, self).__init__(*args, **kwargs)
        self.base_url = "https://www.sothebys.com"
        self.db_client = DatabaseClient()
        failed_lots = self.db_client.query_items(
            table_name="failed_lots", 
        )