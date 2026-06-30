import re
import logging
from collections import Counter

from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.helpers import (
    extract_date,
    find_continent,
    generate_external_id,
    month_to_quarter,
    extract_date,
    parse_all_valid_quantity_volume,
    parse_unit_format,
    extract_all_volume_units,
    convert_to_volume,
    build_lot_external_id,
    BonhamsLotParser,
)

class BonhamsClient:
    def __init__(self):
        self.base_url = "https://www.bonhams.com"
        self.api_url = "https://api01.bonhams.com/search-proxy/multi_search?use_cache=true&enable_lazy_filter=true"
        self.lot_parser = BonhamsLotParser()
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "accept": "application/json, text/plain, */*",
            # "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7",
            "content-type": "application/json",
            "origin": "https://www.bonhams.com",
            "priority": "u=1, i",
            "referer": "https://www.bonhams.com/",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "x-typesense-api-key": "7YZqOyG0twgst4ACc2VuCyZxpGAYzM0weFTLCC20FQY"
        }
    
    def get_auction_search_payload(self, page: int = 1, per_page: int = 250) -> dict:
        return {
            "searches": [
                {
                    "collection": "auctions-search",
                    "exclude_fields": "description",
                    "filter_by": "(biddingStatus:=EN) && (brand:=[`bonhams`, `skinner`, `cornette`, `bonhams-cars`]) && (categories.name:=[`Wine & Whisky`]) && (auctionType:=[`ONLINE`, `PUBLIC`])",
                    "facet_by": "",
                    "query_by": "auctionHeading,auctionTitle,departments.name",
                    "sort_by": "hammerTime.timestamp:desc,auctionTitle:desc",
                    "page": page,
                    "per_page": per_page,
                    "max_facet_values": 300,
                    "q": ""
                }
            ]
        }

    def get_lot_search_payload(self, auction_id: str, page: int = 1, per_page: int = 250) -> dict:
        return {
            "searches": [
                {
                    "collection": "lots",
                    "exclude_fields": "footnotes",
                    "filter_by": f"(auctionId:={auction_id})",
                    "facet_by": "",
                    "query_by": "lotId,title",
                    "sort_by": "lotNo.number:asc,lotNo.full:asc,lotNo.letter:asc",
                    "page": page,
                    "per_page": per_page,
                    "max_facet_values": 300,
                    "q": ""
                }
            ]
        }
    
    def parse_auction_api_response(self, response: dict) -> list[AuctionItem]:
        auctions = []
        documents = response['results'][0]['hits']

        for document in documents:
            document = document.get("document")

            try:
                location = document.get("dates").get("start").get("timezone").get("iana")
                country, city = location.split("/")

                auction_item = AuctionItem()
                auction_item['external_id'] = document.get("id")
                auction_item['auction_title'] = document.get("auctionTitle")
                auction_item['auction_house'] = "Bonhams"
                auction_item['city'] = re.sub(r'[^\w\s\u4e00-\u9fff]', '', city)
                try:
                    auction_item['continent'] = find_continent(country)
                except Exception as e:
                    self.logger.error(f"Error finding continent for country {country}: {e}")
                auction_item['start_date'] = extract_date(document.get("dates").get("start").get("datetime"))
                auction_item['end_date'] = extract_date(document.get("dates").get("end").get("datetime"))
                auction_item['year'] = int(document.get("year"))
                auction_item['quarter'] = month_to_quarter(document.get("month"))
                auction_item['auction_type'] = document.get("auctionType")
                auction_item['url'] = f"{self.base_url}/auction/{document.get("id")}/{generate_external_id(document.get("auctionTitle"))}"

                auctions.append(auction_item)
            except Exception as e:
                self.logger.error(f"Error parsing auction document: {e}")
                continue

        return auctions
    
    def parse_lot_api_response(self, response: dict) -> list:
        lots = []
        documents = response['results'][0]['hits']
        for document in documents:
            document = document.get("document")

            lot_item = LotItem()
            lot_item['auction_id'] = document.get("auctionId")
            lot_item['external_id'] = build_lot_external_id(lot_item['auction_id'], document.get("id"))
            lot_item['lot_name'] = document.get("title")
            lot_item['lot_type'] = [document.get("department").get("name")] if document.get("department") else ["Wine & Spirits"]
            lot_item['original_currency'] = document.get("currency").get("iso_code")
            price = document.get("price").get("hammerPrice")
            lot_item['end_price'] = document.get("price").get("hammerPrice") if price and price > 0 else None
            lot_item['low_estimate'] = document.get("price").get("estimateLow")
            lot_item['high_estimate'] = document.get("price").get("estimateHigh")
            lot_item['sold'] = document.get("status") == "SOLD"
            lot_item['sold_date'] = extract_date(document.get("hammerTime").get("datetime"))
            lot_item['region'] = document.get("region").get("name") if document.get("region") else None
            lot_item['country'] = document.get("country").get("name") if document.get("country") else None
            lot_item['success'] = True
            lot_item['url'] = None

            try:
                lot_item['volume'], lot_item['unit'] = self.parse_whisky_volume(document.get("title"))
                if not lot_item['volume'] or not lot_item['unit']:
                    lot_item['volume'], lot_item['unit'] = self.parse_wine_volume(document.get("title"))
            except Exception as e:
                self.logger.error(f"Error parsing volume and unit from title: {e}")
                lot_item['success'] = False

            lot_detail_items = []
            region_list = []
            country_list = []

            components = self.lot_parser.parse_components(
                document.get("title"),
                document.get("catalogDesc"),
            )

            for component in components:
                region_list.append(component.region) if component.region else None
                inferred_country = self.lot_parser.infer_country(component.region)
                country_list.append(inferred_country) if inferred_country else None

                lot_detail_item = LotDetailItem()
                lot_detail_item['lot_id'] = lot_item['external_id']
                lot_detail_item['lot_producer'] = component.producer
                lot_detail_item['vintage'] = int(component.vintage) if component.vintage else None
                lot_detail_item['unit_format'] = component.unit_format
                lot_detail_items.append(lot_detail_item)

            if region_list:
                lot_item['region'] = Counter(region_list).most_common(1)[0][0]
            if country_list:
                lot_item['country'] = Counter(country_list).most_common(1)[0][0]

            lots.append((lot_item, lot_detail_items))

        return lots
    
    def parse_whisky_volume(self, title: str) -> tuple:
        results = parse_all_valid_quantity_volume(title)
        volume = 0
        total_unit = 0
        for unit, unit_format in results:
            volume += unit * parse_unit_format(unit_format)
            total_unit += unit
        return volume, total_unit
    
    def parse_wine_volume(self, title: str) -> tuple:
        results = extract_all_volume_units(title)
        volume = 0
        total_unit = 0
        for unit, unit_format in results:
            volume += unit * convert_to_volume(unit_format)
            total_unit += unit
        return volume, total_unit
