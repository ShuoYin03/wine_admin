import os
import scrapy

class ZachysSpider(scrapy.Spider):
    name = "zachys_spider"
    allowed_domains = [
        "bid.zachys.com"
    ]
    

    def __init__(self, *args, **kwargs):
        super(ZachysSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        with open("zachys.html", "wb") as f:
            f.write(response.body)

        auctions = response.css("div.auction-item")
        for auction in auctions:
            yield {
                "title": auction.css("h2::text").get(),
                "date": auction.css("span.date::text").get(),
                "status": auction.css("span.status::text").get(),
            }