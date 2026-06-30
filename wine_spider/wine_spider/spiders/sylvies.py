import os
import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
import scrapy
import dotenv
import pandas as pd
from bs4 import BeautifulSoup
from shared.database.auctions_client import AuctionsClient
from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.spiders.logging_utils import build_spider_log_file
from wine_spider.helpers import (
    extract_price_range,
    symbol_to_currency,
    extract_volume_unit,
    convert_to_volume,
    month_to_quarter,
    parse_pdf,
    build_lot_external_id,
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class SylviesSpider(BaseAuctionSpider):
    name = "sylvies_spider"
    allowed_domains = [
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": build_spider_log_file("sylvies.log"),
        "LOG_LEVEL": os.getenv("SYLVIES_LOG_LEVEL", "WARNING"),
        "CONCURRENT_REQUESTS": int(os.getenv("SYLVIES_CONCURRENT_REQUESTS", "8")),
        "CONCURRENT_REQUESTS_PER_DOMAIN": int(os.getenv("SYLVIES_CONCURRENT_REQUESTS_PER_DOMAIN", "8")),
        "AUTOTHROTTLE_TARGET_CONCURRENCY": float(os.getenv("SYLVIES_AUTOTHROTTLE_TARGET_CONCURRENCY", "8")),
        "AUTOTHROTTLE_START_DELAY": float(os.getenv("SYLVIES_AUTOTHROTTLE_START_DELAY", "0.2")),
        "AUTOTHROTTLE_MAX_DELAY": float(os.getenv("SYLVIES_AUTOTHROTTLE_MAX_DELAY", "3")),
        "RETRY_TIMES": int(os.getenv("SYLVIES_RETRY_TIMES", "5")),
        "DOWNLOAD_TIMEOUT": int(os.getenv("SYLVIES_DOWNLOAD_TIMEOUT", "90")),
        # "JOBDIR": "wine_spider/crawl_state/sylvies",
    }

    def __init__(self, *args, **kwargs):
        super(SylviesSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))
        self.auction_client = AuctionsClient()
        self.backfill_auction_ids = {
            auction_id.strip()
            for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
            if auction_id.strip()
        }

    start_urls = ["https://www.sylvies.be/en/ended-auctions"]
        
    def parse(self, response):
        history_auctions = response.css("div.history")
        auction_link_elements = history_auctions.css('a[href^="/en/auction/"]')
        for auction_link_element in auction_link_elements:
            auction_url = response.urljoin(auction_link_element.css('::attr(href)').get())
            auction_title = auction_link_element.css('::text').get().strip()
            modified_auction_title = auction_title.replace(" ", "-").lower()
            if auction_url.startswith("https://www.sylvies.be/en/auction/0/"):
                continue
            
            auction_item = AuctionItem()
            auction_item['external_id'] = f"sylvies_{modified_auction_title}"
            auction_item['auction_title'] = auction_title
            auction_item['auction_house'] = "Sylvie's"
            auction_item['auction_type'] = "PAST"
            auction_item['start_date'] = None
            auction_item['end_date'] = None
            auction_item['year'] = int(auction_title.split(" ")[-1])
            auction_item['quarter'] = int(month_to_quarter(auction_title.split(" ")[0]))
            auction_item['url'] = auction_url

            if self.backfill_auction_ids and auction_item["external_id"] not in self.backfill_auction_ids:
                self.logger.debug(f"Auction {auction_item['external_id']} is not in BACKFILL_AUCTION_IDS. Skipping...")
                continue

            if self.should_skip_existing_auction(auction_item["external_id"], self.auction_client):
                continue
            
            yield scrapy.Request(
                auction_url, 
                callback=self.parse_auction,
                errback=self.parse_auction_error,
                meta={
                    'auction_id': auction_item['external_id'],
                    'auction_item': auction_item
                }
            )

    def parse_auction(self, response):
        auction_id = response.meta.get('auction_id', None)
        auction_item = response.meta.get('auction_item', None)
        
        pdf_link = response.css("a.btn_link::attr(href)").get()
        if pdf_link:
            pdf_link = response.urljoin(pdf_link)
            yield scrapy.Request(
                url=pdf_link,
                callback=self.parse_pdf,
                meta={'auction_item': auction_item}
            )

        try:
            appellation_html = response.css("div.multiselectbox_select.select_appelation").get()
            appellation_json = self.parse_appellation(appellation_html)

            whole_container = response.css("div.auction_lots")
            lot_containers = whole_container.css("div.auction_item")
            for lot_container in lot_containers:
                for item in self.parse_lot_container(response, auction_id, lot_container, appellation_json):
                    yield item

        except Exception:
            self.logger.exception(f"Error parsing auction {auction_id}")

        next_page = response.xpath('//a[@title="Next page"]/@href').get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page), 
                callback=self.parse_auction,
                errback=self.parse_auction_error,
                meta={
                    'auction_id': auction_id,
                    'auction_item': auction_item,
                    'pagination_failures': 0,
                }
            )

    def parse_auction_error(self, failure):
        request = failure.request
        auction_id = request.meta.get('auction_id')
        failures = request.meta.get('pagination_failures', 0) + 1
        self.logger.warning(
            "Sylvie's auction page failed: auction_id=%s url=%s failures=%s error=%s",
            auction_id,
            request.url,
            failures,
            failure.getErrorMessage(),
        )

        if failures >= 3:
            self.logger.warning(
                "Stopping Sylvie's pagination recovery after %s consecutive failures: auction_id=%s url=%s",
                failures,
                auction_id,
                request.url,
            )
            return

        next_url = self.increment_page_url(request.url)
        if not next_url:
            return

        meta = dict(request.meta)
        meta['pagination_failures'] = failures
        yield scrapy.Request(
            url=next_url,
            callback=self.parse_auction,
            errback=self.parse_auction_error,
            meta=meta,
            dont_filter=True,
        )

    def parse_lot_container(self, response, auction_id, lot_container, appellation_json):
        try:
            price_info = lot_container.css("div.large-2.columns.auction_infos")
            estimated_price = price_info.css("div.lot_estimate + p::text").get()
            realized_price = price_info.css("div.lot_my_bid + p::text").get()
            lot_item_infos = lot_container.css("div.lot_item")
            lot_titles = self.extract_visible_lot_titles(lot_item_infos)
            source_lot_id = self.extract_source_lot_id(lot_container)
            if not source_lot_id:
                lot_number = lot_container.css("p.lot_nr a::text").get()
                self.logger.warning(
                    "Skipping Sylvie's lot without source lot id: auction_id=%s lot_number=%s url=%s",
                    auction_id,
                    lot_number,
                    response.url,
                )
                return

            lot_item = LotItem()
            lot_item['auction_id'] = auction_id
            lot_item['external_id'] = build_lot_external_id(auction_id, source_lot_id)
            lot_item['lot_name'] = "; ".join(lot_titles) if lot_titles else f"Lot {lot_container.css('p.lot_nr a::text').get()}"
            lot_item['lot_type'] = ["Wine"]
            lot_item['original_currency'] = self.extract_currency(estimated_price)
            lot_item['end_price'] = self.parse_price_amount(realized_price) if realized_price and "This lot" not in realized_price else None
            lot_item['low_estimate'], lot_item['high_estimate'] = extract_price_range(estimated_price) if estimated_price else (None, None)
            lot_item['sold'] = True if realized_price and "This lot" not in realized_price else False
            lot_item['success'] = True
            lot_item['url'] = response.urljoin(lot_container.css("p.lot_nr a::attr(href)").get())

            volume_count = 0
            unit_count = 0
            lot_detail_items = []
            for lot_item_info in lot_item_infos:
                link_text = lot_item_info.css("a::text").get() or ""
                if (
                    lot_item_info.css("div.lot_description::text").get() is None
                    and "Show other" in link_text
                ):
                    continue

                lot_detail_item = LotDetailItem()
                lot_detail_item['lot_id'] = lot_item['external_id']

                title = self.extract_lot_title(lot_item_info)
                producer = self.extract_producer_from_lot_title(title)
                if producer:
                    lot_detail_item['lot_producer'] = producer

                description = lot_item_info.css("div.lot_description::text").get()
                self.apply_appellation_metadata(lot_item, description, appellation_json)

                lot_detail_item['vintage'] = self.extract_vintage_from_lot_title(title)
                bottle_text = lot_item_info.css("div.lot_bottle::text").get()
                unit, lot_detail_item['unit_format'] = extract_volume_unit(bottle_text.strip()) if bottle_text else (None, None)
                volume = convert_to_volume(lot_detail_item['unit_format']) if lot_detail_item['unit_format'] else None
                volume_count += unit * volume if unit and volume else 0
                unit_count += unit if unit else 0
                lot_detail_items.append(lot_detail_item)

            lot_item['volume'] = volume_count if volume_count > 0 else None
            lot_item['unit'] = unit_count if unit_count > 0 else None
            yield lot_item

            for lot_detail_item in lot_detail_items:
                yield lot_detail_item

        except Exception:
            lot_number = lot_container.css("p.lot_nr a::text").get()
            self.logger.exception(
                "Error parsing Sylvie's lot: auction_id=%s lot_number=%s url=%s",
                auction_id,
                lot_number,
                response.url,
            )

    def parse_pdf(self, response):
        auction_item = response.meta.get('auction_item', None)
        dates = parse_pdf(
            response.body,
            default_year=auction_item.get("year") if auction_item else None,
        )
        auction_item['start_date'] = dates.get('start_date')
        auction_item['end_date'] = dates.get('end_date')

        yield auction_item

    def extract_source_lot_id(self, lot_container):
        for lot_class in lot_container.css("div.lot_item::attr(class)").getall():
            match = re.search(r"\blot_(\d+)\b", lot_class or "")
            if match:
                return match.group(1)
        lot_href = lot_container.css("p.lot_nr a::attr(href)").get()
        match = re.search(r"/lot/(\d+)(?:[/?#]|$)", lot_href or "")
        if match:
            return match.group(1)
        return None

    def extract_currency(self, price_text):
        if not price_text:
            return None
        text = price_text.strip()
        if text.upper().startswith("EUR"):
            return "EUR"
        if text.upper().startswith("CHF"):
            return "CHF"
        return symbol_to_currency(text[0])

    def parse_price_amount(self, price_text):
        if not price_text:
            return None
        match = re.search(r"[\d,.]+", price_text)
        if not match:
            return None
        return float(match.group(0).replace(",", ""))

    def increment_page_url(self, url):
        split = urlsplit(url)
        query = parse_qs(split.query, keep_blank_values=True)
        page_values = query.get("page")
        if not page_values:
            return None

        try:
            page = int(page_values[-1])
        except (TypeError, ValueError):
            return None

        query["page"] = [str(page + 1)]
        return urlunsplit((
            split.scheme,
            split.netloc,
            split.path,
            urlencode(query, doseq=True),
            split.fragment,
        ))

    def extract_visible_lot_titles(self, lot_item_infos):
        titles = []
        seen = set()
        for lot_item_info in lot_item_infos:
            title = self.extract_lot_title(lot_item_info)
            if title and title not in seen:
                titles.append(title)
                seen.add(title)
        return titles

    def extract_lot_title(self, lot_item_info):
        title = lot_item_info.css("div.lot_name a::text").get()
        return title.strip() if title else None

    def extract_vintage_from_lot_title(self, title):
        if not title:
            return None
        match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", title)
        return match.group(1) if match else None

    def extract_producer_from_lot_title(self, title):
        if not title:
            return None
        producer = re.sub(r"^\s*(?:18\d{2}|19\d{2}|20\d{2}|NV|N\.V\.)\s+", "", title, flags=re.IGNORECASE)
        producer = re.sub(r"\([^)]*\)", " ", producer)
        producer = re.sub(r"\b(18\d{2}|19\d{2}|20\d{2})\b", " ", producer)
        producer = re.sub(r"\s+", " ", producer).strip(" ,;-")
        return producer or None

    def apply_appellation_metadata(self, lot_item, description, appellation_json):
        if not description or "|" not in description:
            return

        appellation = description.split("|")[0].strip()
        normalized = self.standardize_appellation(appellation)
        wines = appellation_json.get("wines", {})
        spirits = appellation_json.get("spirits", {})
        portsherry = appellation_json.get("portsherry", {})

        if normalized in spirits:
            lot_item['lot_type'] = ["Spirits"]
            return
        if normalized in portsherry:
            lot_item['lot_type'] = ["Port & Sherry"]
            return

        if normalized in wines:
            lot_item['country'] = self.pretty_appellation(normalized)
            lot_item['lot_type'] = ["Wine"]
            return

        for country, regions in wines.items():
            if normalized == country:
                lot_item['country'] = self.pretty_appellation(country)
                lot_item['lot_type'] = ["Wine"]
                return
            for region, sub_regions in (regions or {}).items():
                if normalized == region:
                    lot_item['region'] = self.pretty_appellation(region)
                    lot_item['country'] = self.pretty_appellation(country)
                    lot_item['lot_type'] = ["Wine"]
                    return
                if normalized in sub_regions:
                    lot_item['region'] = self.pretty_appellation(region)
                    lot_item['sub_region'] = appellation
                    lot_item['country'] = self.pretty_appellation(country)
                    lot_item['lot_type'] = ["Wine"]
                    return

    def standardize_appellation(self, text):
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r'[^a-z]', '', text.lower())

    def pretty_appellation(self, text):
        known = {
            "france": "France",
            "bordeaux": "Bordeaux",
            "burgundy": "Burgundy",
            "bourgogne": "Burgundy",
        }
        return known.get(text, text.title())
    
    def parse_appellation(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        result = {}
        main_ul = soup.find('ul')
        if not main_ul:
            return result

        current_category = None
        current_country = None

        for li in main_ul.find_all('li', recursive=False):
            if 'multiselectbox_title' in li.get('class', []):
                raw_category = li.get_text().strip()
                std_category = self.standardize_appellation(raw_category)
                result[std_category] = {}
                current_category = std_category
                current_country = None
                continue

            if current_category is None:
                continue

            label = li.find('label')
            if not label:
                continue

            text = label.get_text().strip()
            name = re.sub(r'\s*\(\d+\)\s*$', '', text).strip()
            std_name = self.standardize_appellation(name)
            if not name:
                continue

            if 'sub' not in li.get('class', []):
                current_country = std_name
                result[current_category][current_country] = {}
            else:
                if current_country and current_country in result[current_category]:
                    result[current_category][current_country][std_name] = []

                    nested_ul = li.find('ul')
                    if nested_ul:
                        for sub_li in nested_ul.find_all('li', class_='sub_sub'):
                            sub_label = sub_li.find('label')
                            if sub_label:
                                sub_text = sub_label.get_text().strip()
                                sub_name = re.sub(r'\s*\(\d+\)\s*$', '', sub_text).strip()
                                std_sub_name = self.standardize_appellation(sub_name)
                                if std_sub_name:
                                    result[current_category][current_country][std_name].append(std_sub_name)

        return result
