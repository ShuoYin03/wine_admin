import scrapy

class ZachysSpider(scrapy.Spider):
    name = "zachys"
    allowed_domains = ["zachys.com"]
    start_urls = ["https://www.zachys.com/"]

    def parse(self, response):
        # Add your parsing logic here
        pass