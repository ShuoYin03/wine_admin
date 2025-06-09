import os
import re
import json
import scrapy
import dotenv
import pandas as pd
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import (
    generate_external_id,
    extract_month_year_and_format,
    find_continent,
    symbol_to_currency,
    remove_commas,
    extract_price_range,
    extract_years,
    match_lot_info,
    expand_to_lot_items
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class TajanSpider(scrapy.Spider):
    name = "tajan_spider"
    allowed_domains = [
        "www.tajan.com",
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "tajan_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/tajan",
    }

    def __init__(self, *args, **kwargs):
        super(TajanSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.tajan.com/en/past/",
            callback=self.parse,
            meta={
                "playwright": True
            },
        )

    def parse(self, response):
        container = response.css("div#plab__results-container")
        auctions = container.css("div.widget-event")

        for auction in auctions:
            title = auction.css("h2.event__title a::text").get().strip().lower()
            if "wine" in title or "spirits" in title:
                auction_item = AuctionItem()
                auction_item["external_id"] = f"tajan_{generate_external_id(title)}"
                auction_item["auction_title"] = auction.css("h2.event__title a::text").get().strip()
                auction_item["auction_house"] = "Tajan"
                auction_item["city"] = auction.css("div.event__location.mb-0::text").get().split(",")[0].strip()
                auction_item["continent"] = find_continent(auction.css("div.event__location.mb-0::text").get().split(",")[0].strip())
                raw_date_html = auction.css("div.event__date").get()
                raw_dates = self.extract_raw_dates_from_event_date(raw_date_html)
                if len(raw_dates) == 1:
                    month, year, start_date = extract_month_year_and_format(raw_dates[0])
                    auction_item["start_date"] = start_date
                    auction_item["year"] = year
                    auction_item["quarter"] = (month - 1) // 3 + 1
                elif len(raw_dates) == 2:
                    print(raw_dates)
                    month, year, start_date = extract_month_year_and_format(raw_dates[0])
                    _, _, end_date = extract_month_year_and_format(raw_dates[1])
                    auction_item["start_date"] = start_date
                    auction_item["end_date"] = end_date
                    auction_item["year"] = year
                    auction_item["quarter"] = (month - 1) // 3 + 1
                auction_item["auction_type"] = "PAST"
                auction_url = auction.css("h2.event__title a::attr(href)").get()
                auction_item["url"] = auction_url
                yield auction_item

                yield response.follow(
                    auction_url,
                    self.enter_auction_page,
                    meta={
                        "playwright": True,
                        "auction_id": generate_external_id(title)
                    }
                )

        next_page = response.css("a.next.pagination::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page, 
                self.parse,
                meta={
                    "playwright": True
                }
            )
    
    def enter_auction_page(self, response):
        auction_link = response.css("div.sale-ctas a::attr(href)").get()
        if auction_link and auction_link.startswith("https://www.calameo.com"):
            auction_link = None
            for a in response.css("div.sale-ctas a"):
                text = a.css("::text").get()
                if text and ("view auction" in text.lower() or "browse lots" in text.lower()):
                    auction_link = a.css("::attr(href)").get()
                    break

        if auction_link:
            yield response.follow(
                url=f"{auction_link}?displayNum=180&pageNum=1",
                callback=self.parse_auction_page,
                meta={
                    "playwright": True,
                    "auction_id": response.meta.get("auction_id", None)
                }
            )
        else:
            self.logger.warning(f"No auction link found for URL: {response.url}")
            # yield response.replace(
            #     callback=self.parse_auction_page,
            #     meta={
            #         "playwright": True,
            #         "auction_id": response.meta.get("auction_id", None)
            #     }
            # )
            yield from self.parse_auction_page(response)
    
    def parse_auction_page(self, response):
        auction_id = response.meta.get("auction_id", None)

        lots = response.css("div.row.lot-container > div")
        for lot in lots:
            lot_item = LotItem()
            lot_title = lot.css("h2.lot-title-block a::text").get().strip()
            lot_id = lot_title.split(": ")[0].strip()
            lot_name = lot_title.split(": ")[1].strip()
            lot_item["external_id"] = f"tajan_{auction_id}_{lot_id}"
            lot_item["auction_id"] = f"tajan_{auction_id}"
            lot_item["lot_name"] = lot_name
            lot_item["lot_type"] = ["Wine & Spirits"]
            estimate_info = lot.css("p.lot-estimate::text").get()
            currency = symbol_to_currency(estimate_info.split(": ")[1][0])
            lot_item["original_currency"] = currency
            price_info_element = lot.css("div.realized.mb-2")
            price_info = price_info_element.css("span::text").get()
            lot_item["end_price"] = float(remove_commas(price_info[1:])) if price_info else None
            low_estimate, high_estimate = extract_price_range(estimate_info.split(":")[1])
            lot_item["low_estimate"] = low_estimate
            lot_item["high_estimate"] = high_estimate
            lot_item["sold"] = lot_item["end_price"] is not None and lot_item["end_price"] > 0
            lot_item["success"] = True
            url = lot.css("h2.lot-title-block a::attr(href)").get()
            lot_item["url"] = f"https://www.tajan.com{url}"

            vintage = extract_years(lot_name)

            try:
                lot_producer, region, sub_region, country = match_lot_info(lot_item["lot_name"], self.lwin_df)
                lot_producer = [lot_producer] if lot_producer else []
                lot_item["region"] = region
                lot_item["sub_region"] = sub_region
                lot_item["country"] = country
            except Exception as e:
                lot_producer = []
                lot_item['success'] = False

            yield lot_item

            lot_detail_items = expand_to_lot_items(lot_producer, vintage, [], [])
            
            for lot_detail_item in lot_detail_items:
                lot_detail_item["lot_id"] = lot_item["external_id"]
                yield lot_detail_item
        
        last_page = response.css("ol.pagination.justify-content-center > li:last-child a::attr(href)").get()
        if last_page and last_page != "#":
            yield response.follow(
                url=last_page,
                callback=self.parse_auction_page,
                meta={
                    "playwright": True,
                    "auction_id": auction_id
                }
            )
    
    def extract_raw_dates_from_event_date(self, html: str) -> list[str]:
        html = re.sub(r"<br\s*/?>", " - ", html, flags=re.IGNORECASE)
        html = re.sub(r",\s*\d{1,2}\.\d{2}\s*(AM|PM)?(\s*[A-Z]{2,5})?", "", html)
        parts = [p.strip() for p in html.split(" - ") if p.strip()]
        return parts