from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.helpers import (
    extract_date,
    extract_year,
    parse_description,
    build_lot_external_id,
)
from wine_spider.services.lot_information_finder import LotInformationFinder
from collections import Counter
import logging
import re
import unicodedata


SPIRIT_KEYWORDS = (
    "armagnac",
    "bourbon",
    "brandy",
    "cognac",
    "gin",
    "glenfiddich",
    "glenlivet",
    "lagavulin",
    "macallan",
    "rum",
    "rhum",
    "scotch",
    "single malt",
    "vodka",
    "whiskey",
    "whisky",
)

WINE_KEYWORDS = (
    "barbaresco",
    "barolo",
    "bordeaux",
    "bourgogne",
    "burgundy",
    "champagne",
    "chateau",
    "chianti",
    "clos",
    "domaine",
    "pauillac",
    "riesling",
    "rioja",
    "saint-emilion",
    "sauternes",
    "toscana",
)

WINE_CONTEXT_KEYWORDS = (
    "wein",
    "weine",
    "weinauktion",
    "wine",
)

ESTIMATE_RANGE_PATTERN = re.compile(
    r"(?:estimate\s*price|sch[a-zä]+tzpreis)\s*:?\s*"
    r"([0-9][0-9'.,]*)\s*[-–]\s*([0-9][0-9'.,]*)",
    re.IGNORECASE,
)


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
        return f"https://auktionen.steinfelsweine.ch/api/lots?cat_id={auction_catalog_id}&my=false&s=&consignments_only=false&%24sortby=lot_number&%24sortdir=asc&%24page={page}&%24maxpagesize=100"

    def build_classification_context(self, response: dict) -> str:
        related = response.get("@related") or {}
        values = []
        for key in ("auctions", "catalogs", "parts"):
            related_items = related.get(key) or []
            if isinstance(related_items, dict):
                related_items = [related_items]
            for related_item in related_items:
                for field in ("title", "description", "info"):
                    value = related_item.get(field)
                    if value:
                        values.append(str(value))
        return " ".join(values)

    def classify_lot_type(self, lot: dict, parse_result: dict, context_text: str = "") -> str:
        text = " ".join(
            str(value)
            for value in (
                lot.get("shortDescription"),
                lot.get("description"),
                lot.get("details"),
                parse_result.get("title"),
                parse_result.get("producer"),
            )
            if value
        )
        normalized_text = self.normalize_classification_text(text)
        normalized_context = self.normalize_classification_text(context_text)

        if self.contains_keyword(normalized_text, SPIRIT_KEYWORDS):
            return "Spirits"
        if (
            self.contains_keyword(normalized_text, WINE_KEYWORDS)
            or self.contains_keyword(normalized_context, WINE_CONTEXT_KEYWORDS)
        ):
            return "Wine"
        return "Wine & Spirits"

    def should_match_wine_metadata(self, lot_type: str) -> bool:
        return lot_type == "Wine"

    def normalize_classification_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )
        return re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()

    def contains_keyword(self, text: str, keywords: tuple[str, ...]) -> bool:
        padded_text = f" {text} "
        for keyword in keywords:
            normalized_keyword = self.normalize_classification_text(keyword)
            if f" {normalized_keyword} " in padded_text:
                return True
        return False

    def find_wine_information(self, title: str, should_match: bool):
        if not should_match:
            return None, None, None, None

        try:
            return self.lot_information_finder.find_lot_information(title)
        except Exception as e:
            self.logger.debug(f"Error processing lot title: {title}, Error: {e}")
            return None, None, None, None

    def get_fallback_lot_producer(self, parse_result: dict, lot_type: str, title: str | None = None):
        if lot_type == "Wine":
            return parse_result['title']
        return parse_result.get("producer") or title or parse_result.get("title")

    def parse_estimate_range_from_description(self, description: str | None):
        if not description:
            return None, None

        text = re.sub(r"<[^>]+>", " ", description)
        text = re.sub(r"\s+", " ", text).strip()
        match = ESTIMATE_RANGE_PATTERN.search(text)
        if not match:
            return None, None

        return self.parse_estimate_number(match.group(1)), self.parse_estimate_number(match.group(2))

    def parse_estimate_number(self, value: str):
        normalized = value.replace("'", "").replace(",", "")
        try:
            number = float(normalized)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    
    def parse_auction_api_response(self, response: dict) -> dict:
        auctions = []
        auction_catalog_ids = []

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
            auction_catalog_ids.append(catalog.get("id"))

        return auctions, auction_catalog_ids

    def parse_lot_api_response(self, response: dict, auction_catalog_id: str, url: str) -> dict:
        lots = []
        try:
            auction = response.get("@related").get("auctions")[0]
        except Exception as e:
            if response.get("$itemCount") != 0:
                self.logger.error(f"Auction Not Exist for this url: {url}")
            return lots

        classification_context = self.build_classification_context(response)

        for lot in response.get("items", []):
            parse_result = parse_description(lot.get("description"))
            lot_type = self.classify_lot_type(lot, parse_result, classification_context)
            should_match_wine_metadata = self.should_match_wine_metadata(lot_type)
            lot_item = LotItem()
            lot_item['auction_id'] = f"steinfels_{auction.get("id")}"
            lot_item['external_id'] = build_lot_external_id(lot_item['auction_id'], lot.get("id"))
            lot_item['lot_name'] = parse_result['title']
            lot_item['lot_type'] = [lot_type]
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
            upper_base_price = lot.get("upperBasePrice")
            _, description_high_estimate = self.parse_estimate_range_from_description(
                lot.get("description")
            )
            lot_item['high_estimate'] = (
                upper_base_price
                if isinstance(upper_base_price, (int, float)) and upper_base_price > 0
                else description_high_estimate or lot.get("basePrice")
            )
            lot_item['sold'] = lot.get("state") == "sold"
            lot_item['success'] = True
            lot_item['url'] = self.get_lot_page_url(
                lot_id=lot.get("id"), 
                auction_catalog_id=auction_catalog_id
            )

            if parse_result['sub_items']:
                lot_detail_items = []
                region_list = []
                sub_region_list = []
                country_list = []
                idx = 0
                for sub_item in parse_result['sub_items']:
                    producer, region, sub_region, country = self.find_wine_information(
                        sub_item['title'],
                        should_match_wine_metadata,
                    )

                    lot_detail_item = LotDetailItem()
                    lot_detail_item['lot_id'] = lot_item['external_id']
                    lot_detail_item['lot_producer'] = producer if producer else self.get_fallback_lot_producer(
                        parse_result,
                        lot_type,
                        sub_item.get('title'),
                    )
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
                producer, region, sub_region, country = self.find_wine_information(
                    parse_result['title'],
                    should_match_wine_metadata,
                )
                lot_detail_item = LotDetailItem()
                lot_detail_item['lot_id'] = lot_item['external_id']
                lot_detail_item['lot_producer'] = producer if producer else self.get_fallback_lot_producer(
                    parse_result,
                    lot_type,
                )
                lot_detail_item['vintage'] = parse_result['vintages'][0] if parse_result['vintages'] else None
                lot_detail_item['unit_format'] = parse_result['unit_format']
                lot_detail_items = [lot_detail_item]

                lot_item['region'] = region
                lot_item['sub_region'] = sub_region
                lot_item['country'] = country

            lots.append((lot_item, lot_detail_items))

        return lots
       
