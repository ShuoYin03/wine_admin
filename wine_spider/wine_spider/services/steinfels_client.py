from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.helpers import (
    extract_date,
    extract_year,
    parse_description
)
from wine_spider.services import LotInformationFinder
from collections import Counter
import logging

class SteinfelsClient:
    def __init__(self):
        self.auction_api_url = "https://auktionen.steinfelsweine.ch/api/auctions?archived=true"
        self.lot_api_url = None
        self.lot_information_finder = LotInformationFinder()
        self.logger = logging.getLogger(__name__)

    def get_auction_page_url(self, auction_catalog_id: str) -> str:
        return f"https://auktionen.steinfelsweine.ch/en-us/auctions/lots?$page=1&$maxpagesize=20&$sortby=lot_number&$sortdir=asc&cat_id={auction_catalog_id}"
    
    def get_lot_page_url(self, lot_id: str, auction_catalog_id: str) -> str:
        return f"https://auktionen.steinfelsweine.ch/en-us/auctions/lots/{lot_id}?$page=1&$maxpagesize=20&$sortby=lot_number&$sortdir=asc&cat_id={auction_catalog_id}&$goto={lot_id}"

    def get_lot_api_url(self, auction_catalog_id: str, page: int = 1) -> str:
        return f"https://auktionen.steinfelsweine.ch/api/lots?cat_id={auction_catalog_id}&my=false&s=&consignments_only=false&%24sortby=lot_number&%24sortdir=asc&%24page={page}&%24maxpagesize=1000"
    
    def parse_auction_api_response(self, response: dict) -> dict:
        auctions = []
        auction_catalog_id = []

        for auction in response:
            catalog = auction.get("catalogs")[0]
            auction_item = AuctionItem()
            auction_item['external_id'] = f"steinfels_{str(auction.get("id"))}"
            auction_item['auction_title'] = auction.get("title")
            auction_item['auction_house'] = "Steinfels"
            auction_item['start_date'] = extract_date(auction.get("startDate"))
            auction_item['end_date'] = extract_date(auction.get("endDate"))
            auction_item['year'] = extract_year(auction.get("startDate"))
            auction_item['quarter'] = int(auction.get("startDate").split("-")[1]) // 3 + 1 if auction.get("startDate") else None
            auction_item['auction_type'] = "ONLINE" if catalog.get("isOnline") else "PAST"
            auction_item['url'] = self.get_auction_page_url(catalog.get("id"))

            auctions.append(auction_item)
            auction_catalog_id.append(catalog.get("id"))

        return auctions, catalog.get("id")
    
    def parse_lot_api_response(self, response: dict, auction_catalog_id: str, url: str) -> dict:
        lots = []
        try:
            auction = response.get("@related").get("auctions")[0]
        except Exception as e:
            if response.get("$itemCount") != 0:
                self.logger.error(f"Auction Not Exist for this url: {url}")
            return lots

        for lot in response.get("items", []):
            parse_result = parse_description(lot.get("description"))
            lot_item = LotItem()
            lot_item['external_id'] = f"steinfels_{auction.get("id")}_{lot.get("id")}"
            lot_item['auction_id'] = f"steinfels_{auction.get("id")}"
            lot_item['lot_name'] = parse_result['title']
            lot_item['lot_type'] = ["Wine & Spirits"]
            try:
                lot_item['volume'] = parse_result.get("total_volume_ml")
            except (ValueError, TypeError):
                lot_item['volume'] = None
            try:
                lot_item['unit'] = int(parse_result['quantity'])
            except (ValueError, TypeError):
                lot_item['unit'] = None
            lot_item['original_currency'] = auction.get("currency")
            lot_item['start_price'] = lot.get("startingBid")
            lot_item['end_price'] = lot.get("hammerPrice")
            lot_item['low_estimate'] = lot.get("basePrice")
            lot_item['high_estimate'] = lot.get("upperBasePrice") if "upperBasePrice" in lot and lot.get("upperBasePrice") > 0 else lot.get("basePrice")
            lot_item['sold'] = lot.get("state") == "sold"
            lot_item['success'] = True
            lot_item['url'] = self.get_lot_page_url(
                lot_id=lot.get("id"), 
                auction_catalog_id=auction_catalog_id
            )

            if parse_result['sub_items']:
                lot_detail_items = []
                region_list = sub_region_list = country_list = []
                idx = 0
                for sub_item in parse_result['sub_items']:
                    try:
                        producer, region, sub_region, country = self.lot_information_finder.find_lot_information(sub_item['title'])
                    except Exception as e:
                        self.logger.debug(f"Error processing sub-item: {sub_item['title']}, Error: {e}")
                        producer, region, sub_region, country = None, None, None, None

                    lot_detail_item = LotDetailItem()
                    lot_detail_item['lot_id'] = lot_item['external_id']
                    lot_detail_item['lot_producer'] = producer if producer else parse_result['title']
                    lot_detail_item['vintage'] = sub_item['vintage'] if sub_item['vintage'] else parse_result['vintages'][0] if parse_result['vintages'] else None
                    try:
                        lot_detail_item['unit_format'] = parse_result['unit_format'][idx] if isinstance(parse_result['unit_format'], list) else parse_result['unit_format']
                    except (IndexError):
                        self.logger.error(f"Index error: {parse_result['unit_format']}")
                    idx += 1

                    lot_detail_items.append(lot_detail_item)
                    region_list.append(region) if region else None
                    sub_region_list.append(sub_region) if sub_region else None
                    country_list.append(country) if country else None

                if region_list:
                    lot_item['region'] = Counter(region_list).most_common(1)[0][0]
                if sub_region_list:
                    lot_item['sub_region'] = Counter(sub_region_list).most_common(1)[0][0]
                if country_list:
                    lot_item['country'] = Counter(country_list).most_common(1)[0][0]

            else:
                try:
                    producer, region, sub_region, country = self.lot_information_finder.find_lot_information(parse_result['title'])
                except Exception as e:
                    self.logger.debug(f"Error processing lot title: {parse_result['title']}, Error: {e}")
                    producer, region, sub_region, country = None, None, None, None
                lot_detail_item = LotDetailItem()
                lot_detail_item['lot_id'] = lot_item['external_id']
                lot_detail_item['lot_producer'] = producer if producer else parse_result['title']
                lot_detail_item['vintage'] = parse_result['vintages'][0] if parse_result['vintages'] else None
                lot_detail_item['unit_format'] = parse_result['unit_format']
                lot_detail_items = [lot_detail_item]

                lot_item['region'] = region
                lot_item['sub_region'] = sub_region
                lot_item['country'] = country

            lots.append((lot_item, lot_detail_items))

        return lots
       