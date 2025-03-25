import os
import scrapy
import dotenv
from scrapy_playwright.page import PageMethod

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ZachysSpider(scrapy.Spider):
    name = "zachys_spider"
    allowed_domains = [
        "bid.zachys.com"
    ]

    def __init__(self, *args, **kwargs):
        super(ZachysSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        url = "https://bid.zachys.com/auctions?page=1&status=5"
        yield scrapy.Request(
            url=url,
            callback=self.parse,
            meta={
                "playwright": True,
                "playwright_context": "default",
                "playwright_include_page": True,
                "playwright_page_coroutines": [
                    PageMethod(
                        "set_user_agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    ),
                    PageMethod("evaluate", "window.AwsWafIntegration.getToken();"),
                    PageMethod("wait_for_timeout", 2000),
                    PageMethod("wait_for_selector", "div.auction-item"),
                ],
            },
        )

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