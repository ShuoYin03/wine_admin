import os
import scrapy
import dotenv
from datetime import datetime
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import (
    remove_commas,
    wineauctioneer_parse_date,
    parse_unit_format,
    extract_unit_and_unit_format,
    expand_to_lot_items
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class WineAuctioneerSpider(scrapy.Spider):
    name = "wineauctioneer_spider"
    allowed_domains = [
        "www.wineauctioneer.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "wineauctioneer_log.txt",
        "WINEAUCTIONEER_STATE_PATH": "wine_spider/login_state/wineauctioneer_cookies.json",
        "WINEAUCTIONEER_STATE_EXPIRE_DAYS" : 107,
        "WINEAUCTIONEER_LOGIN_SCRIPT": "wine_spider/helpers/wineauctioneer/login.py",
        "PLAYWRIGHT_CONTEXTS": {
            "wineauctioneer": {
                "storage_state": "wine_spider/login_state/wineauctioneer_cookies.json"
            }
        },
        "DOWNLOADER_MIDDLEWARES": {
            'wine_spider.middlewares.wineauctioneer_login_middleware.WineauctioneerLoginMiddleware': 100,
        }
    }

    start_urls = [
        "https://wineauctioneer.com/wine-auctions#past-auctions"
    ]

    def __init__(self, *args, **kwargs):
        super(WineAuctioneerSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        auction_links = response.css("a.btn[href*='/wine-auctions/'][href$='/lots']::attr(href)").getall()
        auction_links = set(auction_links)
        
        for link in auction_links:
            yield response.follow(link, self.parse_auction, dont_filter="true")
    
    def parse_auction(self, response):
        auction_item = AuctionItem()
        auction_item["external_id"] = response.css("h1.page-title::text").get().strip().replace(" ", "-").lower()
        auction_item["auction_title"] = response.css("h1.page-title::text").get().strip()
        auction_item["auction_house"] = "Wineauctioneer"
        auction_item["city"] = None
        auction_item["continent"] = None
        start_date = response.css("div.auction-info.field-hstack div:first-child div::text").get().strip()
        end_date = response.css("div.auction-info.field-hstack div:nth-child(2) div:last-child::text").get().strip()
        auction_item["start_date"] = datetime.strptime(start_date, "%d %B %Y").strftime("%Y-%m-%d")
        auction_item["end_date"] = datetime.strptime(end_date, "%d %B %Y").strftime("%Y-%m-%d")
        auction_item["year"] = auction_item["start_date"][:4]
        auction_item["quarter"] = (int(auction_item['start_date'][5:7]) - 1) // 3 + 1
        auction_item["auction_type"] = response.css("div.auction-status.auction-status-closed::text").get().strip()
        auction_item["url"] = response.url
        yield auction_item

        lot_links = response.css("h3.teaser-title a::attr(href)").getall()
        for link in lot_links:
            yield response.follow(link, self.parse_lot, meta={"auction_id": auction_item["external_id"]}, dont_filter="true")
            break

        next_page = response.xpath('//a[@rel="next"]/@href').get()
        if next_page:
            yield response.follow(next_page, self.parse_auction_next_page, meta={"auction_id": auction_item["external_id"]}, dont_filter="true")

    def parse_auction_next_page(self, response):
        auction_id = response.meta.get("auction_id", None)
        
        lot_links = response.css("h3.teaser-title a::attr(href)").getall()
        for link in lot_links:
            yield response.follow(link, self.parse_lot, meta={"auction_id": auction_id}, dont_filter="true")

        next_page = response.xpath('//a[@rel="next"]/@href').get()
        if next_page:
            yield response.follow(next_page, self.parse_auction_next_page, meta={"auction_id": auction_id}, dont_filter="true")

    def parse_lot(self, response):
        auction_id = response.meta.get("auction_id", None)

        lot_item = LotItem()
        lot_item["external_id"] = response.css("div.mb-1::text").getall()[-1].strip()
        lot_item["auction_id"] = auction_id
        lot_item["lot_name"] = response.css("h1.page-title::text").get().strip()
        lot_type = response.css("div.field.field--name-field-type div.field__item::text").get()
        if lot_type:
            lot_item["lot_type"] = [lot_type.strip()]
        unit_info = response.css("div.field.field--name-field-size div.field__item::text").get()
        unit_format = None
        if unit_info:
            lot_item['volume'] = parse_unit_format(unit_info)
            lot_item['unit'], unit_format = extract_unit_and_unit_format(unit_info)
        price_info_html = response.css("div.bid__stat--text::text").get()
        if price_info_html:
            price_info = price_info_html.strip()
            lot_item["original_currency"] = price_info[0:1]
            lot_item["end_price"] = float(remove_commas(price_info[1:]))
            lot_item["sold"] = True
        else:
            lot_item["original_currency"] = None
            lot_item["end_price"] = None
            lot_item["sold"] = False
        sold_date = response.css("div.auction-info.hstack.gap-4 div > div::text").getall()[-1]
        lot_item["sold_date"] = wineauctioneer_parse_date(sold_date.strip()) if sold_date else None
        lot_item["success"] = True
        lot_item["url"] = response.url
        yield lot_item

        lot_producer = []
        if response.css("div.field.field--name-field-producer div.field__item a::text").get():
            lot_producer.append(response.css("div.field.field--name-field-producer div.field__item a::text").get().strip())
        vintage = []
        if response.css("div.field.field--name-field-vintage div.field__item::text").get():
            vintage.append(response.css("div.field.field--name-field-vintage div.field__item::text").get().strip())
        unit_format = [unit_format] if unit_format else []
        wine_colour = []
        if response.css("div.field.field--name-field-type div.field__item::text").get():
            wine_colour.append(response.css("div.field.field--name-field-type div.field__item::text").get().strip())
        
        lot_detail_items = expand_to_lot_items(
            lot_producer=lot_producer,
            vintage=vintage,
            unit_format=unit_format,
            wine_colour=wine_colour
        )

        for lot_detail_item in lot_detail_items:
            lot_detail_item['lot_id'] = lot_item['external_id']
            yield lot_detail_item