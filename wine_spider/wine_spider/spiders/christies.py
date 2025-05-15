import os
import re
import json
import scrapy
import dotenv
import demjson3
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse, parse_qs
from wine_spider.items import AuctionItem, LotItem
from wine_spider.helpers import (
    find_continent, 
    is_filter_exists,
    expand_to_lot_items,
    map_filter_to_field,
    extract_years_from_json,
    parse_qty_and_unit_from_secondary_title
)
from wine_spider.services import ChristiesClient
from wine_spider.services.lot_information_finder import LotInformationFinder

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class ChristiesSpider(scrapy.Spider):
    name = "christies_spider"
    allowed_domains = [
        "www.christies.com",
        "onlineonly.christies.com"
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "christies_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/christies",
    }

    def __init__(self, *args, **kwargs):
        super(ChristiesSpider, self).__init__(*args, **kwargs)
        self.client = ChristiesClient()
        self.lot_information_finder = LotInformationFinder()

    def start_requests(self):
        year_list = [i for i in range(2007, 2026)]

        for year in year_list:
            for month in range(1, 13):
                url = f"https://www.christies.com/en/results?year={year}&filters=|category_14|&month={month}"

                yield scrapy.Request(
                    url=url,
                    callback=self.parse
                )

    def parse(self, response):
        match = re.search(r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n', response.text, re.DOTALL)
        if not match:
            self.logger.error("calendar not found")
            return

        data = demjson3.decode(match.group(1))
        events = data.get('data', {}).get('events', [])

        for event in events:
            filters = event.get("filter_ids", "")

            if "category_14" in filters:
                auctionItem = AuctionItem()

                auctionItem["auction_title"] = event.get("title_txt", None)
                auctionItem["auction_house"] = "Christie's"
                auctionItem["city"] = event.get("location_txt", None)
                auctionItem["continent"] = find_continent(auctionItem["city"])
                start_date = event.get("start_date", None)
                end_date = event.get("end_date", None)
                auctionItem["start_date"] = datetime.fromisoformat(start_date).date()
                auctionItem["end_date"] = datetime.fromisoformat(end_date).date()
                auctionItem["year"] = auctionItem["start_date"].year if start_date else None
                auctionItem["quarter"] = auctionItem["start_date"].month // 4 + 1 if start_date else None
                auctionItem["auction_type"] = "LIVE" if event.get("is_live", None) else "PAST"
                auctionItem["url"] = event.get("landing_url", None)

                try:
                    if "onlineonly.christies.com" in auctionItem["url"]:
                        parsed = urlparse(auctionItem["url"])
                        qs = parse_qs(parsed.query)
                        sale_id = qs.get("SaleID", [None])[0]
                        sale_number = qs.get("SaleNumber", [None])[0]
                    elif "www.christies.com" in auctionItem["url"]:
                        sale_id = int(auctionItem["url"].split("/")[-2].split("-")[-1])
                        sale_number_text = event.get("subtitle_txt", None)
                        sale_number = int(sale_number_text.split(" ")[2])
                    else:
                        raise ValueError("Invalid URL format")
                    
                    if not sale_number or not sale_id:
                        raise ValueError("Sale number or Sale ID is missing")

                    auctionItem["external_id"] = f"{sale_id}#{sale_number}"
                    yield auctionItem

                    yield scrapy.Request(
                        url=auctionItem["url"],
                        callback=self.parse_auctions,
                        meta={
                            "auction_id": auctionItem["external_id"],
                            "sale_id": sale_id,
                            "sale_number": sale_number,
                        }
                    )

                except Exception as e:
                    self.logger.error(f"Error parsing auction: {e}")      
            
                    
    def parse_auctions(self, response):
        sale_id = response.meta.get("sale_id")
        if response.url.split("/")[-1].strip().isdigit():
            sale_id = int(response.url.split("/")[-1].strip())
        sale_number = response.meta.get("sale_number")
        auction_id = response.meta.get("auction_id")

        pattern = r"window\.chrComponents\s*=\s*(\{.*?\});"
        match = re.search(pattern, response.text, re.DOTALL)
        if not match:
            saved_lots_pattern = r"window\.chrComponents\.lots\s*=\s*(\{.*?\});"
            match = re.search(saved_lots_pattern, response.text, re.DOTALL)
            if not match:
                if response.url != "https://www.christies.com/en/calendar":
                    self.logger.error(f"Failed to find chrComponents in response for auction: {auction_id}")
                return
            
        json_filters = json.loads(match.group(1))
        saved = False
        try:
            filters = json_filters.get("lots", []).get("data", []).get("filters", []).get("groups", [])
            basic_url = self.client.lots_query("paging", sale_id)
        except Exception as e:
            try:
                filters = json_filters.get("data", []).get("filters", []).get("groups", [])
                basic_url = self.client.saved_lots_query("paging", sale_id, sale_number)
                saved = True
            except Exception as e:
                with open("json_filter.json", "w", encoding="utf-8") as f:
                    json.dump(json_filters, f, indent=4)
                return
        
        all_filters = []
        for filter in filters:
            title = filter.get("title_txt", None)
            if is_filter_exists(title):
                filter_items = filter.get("filters", [])
                for item in filter_items:
                    id = item.get("id", None)
                    all_filters.append(id)

        yield scrapy.Request(
            url=basic_url,
            callback=self.parse_initial_request,
            meta={
                "auction_id": auction_id,
                "sale_id": sale_id,
                "sale_number": sale_number,
                "all_filters": all_filters,
                "saved": saved,
            }
        )

    def parse_initial_request(self, response):
        auction_id = response.meta.get("auction_id")
        all_filters = response.meta.get("all_filters")
        sale_id = response.meta.get("sale_id")
        sale_number = response.meta.get("sale_number")
        saved = response.meta.get("saved")

        lots = defaultdict(
            lambda: {
                "lot_item": None, 
                "lot_detail_info": {
                    k: [] for k in [
                        "lot_producer", 
                        "vintage", 
                        "unit_format", 
                        "wine_colour"
                    ]}})
        
        response_data = response.json()['lots']
        for lot in response_data:
            lot_item = LotItem()
            lot_item["external_id"] = lot.get("object_id", None)
            lot_item["auction_id"] = auction_id
            lot_item["lot_name"] = lot.get("title_primary_txt", None)
            lot_item["lot_type"] = ["Wine & Spirits"]
            price_txt = lot.get("price_realised_txt") or lot.get("estimate_txt")
            lot_item["original_currency"] = price_txt.split(" ", 1)[0] if price_txt else None
            lot_item["end_price"] = int(float(lot.get("price_realised"))) if lot.get("price_realised", None) else None
            lot_item["low_estimate"] = int(float(lot.get("estimate_low"))) if lot.get("estimate_low", None) else None
            lot_item["high_estimate"] = int(float(lot.get("estimate_high"))) if lot.get("estimate_high", None) else None
            lot_item["sold"] = True if lot.get("price_realised") else False
            lot_item["sold_date"] = datetime.fromisoformat(lot.get("end_date")).date() if lot.get("end_date") and lot_item['sold'] else None
            lot_item["success"] = True
            lot_item["url"] = response.url

            try:
                volume, unit = parse_qty_and_unit_from_secondary_title(lot.get("title_secondary_txt", None))
            except Exception as e:
                volume = None
                unit = None
                success = False
            lot_item["volume"] = volume
            lot_item["unit"] = unit
            
            lots[lot_item["external_id"]]["lot_item"] = lot_item

            vintage = extract_years_from_json(lot)
            lots[lot_item["external_id"]]["lot_detail_info"]["vintage"] += vintage
        
        if not all_filters:
            self.logger.debug(len(lots))
            yield from self.yield_items(lots, auction_id)
            return

        filter = all_filters.pop(0)
        if filter:
            yield from self.yield_request(saved, auction_id, sale_id, sale_number, all_filters, filter, lots, self.parse_filters)
    
    def parse_filters(self, response):
        auction_id = response.meta.get("auction_id")
        all_filters = response.meta.get("all_filters")
        sale_id = response.meta.get("sale_id")
        sale_number = response.meta.get("sale_number")
        lots = response.meta.get("lots", {})
        saved = response.meta.get("saved", False)
        current_filter = response.meta.get("current_filter", None)

        lots_data = response.json().get("lots", [])
        if lots_data:
            try:
                for lot in lots_data:
                    id = lot.get("object_id", None)
                    lot_item = lots.get(id, None).get("lot_item", None)
                    lot_detail_info = lots.get(id, None).get("lot_detail_info", None)
                    if not lot_item:
                        self.logger.error(f"Lot {id} not found in lots dictionary for auction {auction_id}")
                        continue
                    self.add_data(current_filter, lot_item, lot_detail_info)
            except Exception as e:
                self.logger.error(f"Error parsing lots: {e}")
                return

        if not all_filters:
            yield from self.yield_items(lots, auction_id)
            return
        
        filter = all_filters.pop(0)
        if filter:
            yield from self.yield_request(saved, auction_id, sale_id, sale_number, all_filters, filter, lots, self.parse_filters)

    def yield_items(self, lots, auction_id):
        for lot in lots.values():
            if not lot['lot_detail_info']['lot_producer'] or lot['lot_detail_info']['lot_producer'] == []:
                try:
                    producer, _, _, _ =  self.lot_information_finder.find_lot_information(lot["lot_item"]["lot_name"])
                    lot['lot_detail_info']['lot_producer'].append(producer)
                except Exception as e:
                    self.logger.error(f"Error finding lot information: {e} for lot {lot['lot_item']['external_id']} in auction {auction_id}")
                    lot['lot_item']['success'] = False

            yield lot["lot_item"]

            lot_detail_info = lot["lot_detail_info"]
            lot_detail_items = expand_to_lot_items(
                lot_producer=lot_detail_info["lot_producer"],
                vintage=lot_detail_info["vintage"],
                unit_format=lot_detail_info["unit_format"],
                wine_colour=lot_detail_info["wine_colour"]
            )

            for lot_detail_item in lot_detail_items:
                lot_detail_item["lot_id"] = lot["lot_item"]["external_id"]
                yield lot_detail_item

    def yield_request(self, saved, auction_id, sale_id, sale_number, all_filters, current_filter, lots, callback):
        if not saved:
            yield scrapy.Request(
                url=self.client.lots_query("refinecoa", sale_id, filterids=current_filter),
                callback=callback,
                meta={
                    "auction_id": auction_id,
                    "sale_id": sale_id,
                    "sale_number": sale_number,
                    "all_filters": all_filters,
                    "saved": saved,
                    "lots": lots,
                    "current_filter": current_filter,
                }
            )
        else:
            yield scrapy.Request(
                url=self.client.saved_lots_query("refinecoa", sale_id, sale_number, filterids=current_filter),
                callback=callback,
                meta={
                    "auction_id": auction_id,
                    "sale_id": sale_id,
                    "sale_number": sale_number,
                    "all_filters": all_filters,
                    "saved": saved,
                    "lots": lots,
                    "current_filter": current_filter,
                }
            )

    def add_data(self, filter, lot_item, lot_detail_info):
        type = filter.split("{")[0]
        data = filter.split("{")[1].split("}")[0]
        field = map_filter_to_field(type)
        if field == "lot_producer":
            lot_detail_info[field].append(data)
        elif field == "region":
            lot_item["region"] = data
        elif field == "country":
            lot_item["country"] = data
        elif field == "wine_colour":
            lot_detail_info[field].append(data)
        elif field == "unit_format":
            lot_detail_info[field].append(data)