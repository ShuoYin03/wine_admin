import os
import re
import scrapy
import dotenv
import pandas as pd
from bs4 import BeautifulSoup
from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.helpers import (
    extract_price_range,
    symbol_to_currency,
    extract_volume_unit,
    convert_to_volume,
    month_to_quarter,
    parse_pdf
)

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class SylviesSpider(scrapy.Spider):
    name = "sylvies_spider"
    allowed_domains = [
    ]

    custom_settings = {
        # "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "sylvies_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/sylvies",
    }

    def __init__(self, *args, **kwargs):
        super(SylviesSpider, self).__init__(*args, **kwargs)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lwin_df = pd.read_excel(os.path.join(base_dir, "LWIN wines.xls"))

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
            
            yield scrapy.Request(
                auction_url, 
                callback=self.parse_auction,
                meta={
                    'auction_id': auction_item['external_id'],
                    'auction_item': auction_item
                }
            )

            break

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
                price_info = lot_container.css("div.large-2.columns.auction_infos")
                estimated_price = price_info.css("div.lot_estimate + p::text").get()
                realized_price = price_info.css("div.lot_my_bid + p::text").get()

                lot_item = LotItem()
                lot_item['external_id'] = lot_container.css("div.lot_item::attr(class)").get().strip().split(" ")[-1].split("_")[-1].strip()
                lot_item['auction_id'] = auction_id
                lot_item['lot_name'] = f"sylvies_{auction_id}_{lot_container.css("p.lot_nr a::text").get()}"
                lot_item['lot_type'] = ["Wine"]
                lot_item['original_currency'] = symbol_to_currency(estimated_price.strip()[0]) if estimated_price else None
                lot_item['end_price'] = float(realized_price[1:].strip()) if realized_price and "This lot" not in realized_price else None
                lot_item['low_estimate'], lot_item['high_estimate'] = extract_price_range(estimated_price)
                lot_item['sold'] = True if realized_price and "This lot" not in realized_price else False
                lot_item['success'] = True
                lot_item['url'] = lot_container.css("p.lot_nr a::attr(href)").get()

                volume_count = 0
                unit_count = 0
                lot_detail_items = []
                lot_item_infos = lot_container.css("div.lot_item")
                for lot_item_info in lot_item_infos:
                    if lot_item_info.css("div.lot_description::text").get() is None \
                    and "Show other" in lot_item_info.css("a::text").get():
                        continue
                    lot_detail_item = LotDetailItem()
                    lot_detail_item['lot_id'] = lot_item['external_id']

                    appellation_first = lot_item_info.css("div.lot_description::text").get().split("|")[0].strip()
                    appellation_second = lot_item_info.css("div.lot_description::text").get().split("|")[1].strip()
                    if appellation_first in appellation_json['wines']:
                        lot_item['country'] = appellation_first
                        lot_detail_item['lot_producer'] = appellation_second
                        lot_item['lot_type'] = ["Wine"]
                    elif appellation_first in appellation_json['wines']['france']:
                        lot_detail_item['lot_producer'] = appellation_first
                        lot_item['region'] = appellation_first
                        lot_item['country'] = "France"
                        lot_item['lot_type'] = ["Wine"]
                    elif appellation_first in appellation_json['spirits']:
                        lot_item['lot_type'] = ["Spirits"]
                    elif appellation_first in appellation_json['portsherry']:
                        lot_item['lot_type'] = ["Port & Sherry"]
                    for key, value in appellation_json['wines']['france'].items():
                        if appellation_first in value:
                            lot_item['region'] = key
                            lot_item['country'] = "France"
                            lot_detail_item['lot_producer'] = appellation_first
                            lot_item['lot_type'] = ["Wine"]
                    
                    lot_detail_item['vintage'] = lot_item_info.css("div.lot_name a::text").get().strip()[:4]
                    unit, lot_detail_item['unit_format'] = extract_volume_unit(lot_item_info.css("div.lot_bottle::text").get().strip())
                    volume = convert_to_volume(lot_detail_item['unit_format']) if lot_detail_item['unit_format'] else 0
                    volume_count += unit * volume if unit and volume != 0 else 0
                    unit_count += unit if unit else 0
                    lot_detail_items.append(lot_detail_item)

                lot_item['volume'] = volume_count if volume_count > 0 else None
                lot_item['unit'] = unit_count if unit_count > 0 else None
                yield lot_item

                for lot_detail_item in lot_detail_items:
                    yield lot_detail_item

        except Exception as e:
            self.logger.error(f"Error parsing auction {auction_id}: {e}")

        next_page = response.xpath('//a[@title="Next page"]/@href').get()
        if next_page:
            yield scrapy.Request(
                url=response.urljoin(next_page), 
                callback=self.parse_auction,
                meta={'auction_id': auction_id}
            )

    def parse_pdf(self, response):
        auction_item = response.meta.get('auction_item', None)
        dates = parse_pdf(response.body)
        auction_item['start_date'] = dates.get('start_date')
        auction_item['end_date'] = dates.get('end_date')

        yield auction_item
    
    def parse_appellation(self, html):
        def standardize(text: str) -> str:
            return re.sub(r'[^a-z]', '', text.lower())

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
                std_category = standardize(raw_category)
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
            std_name = standardize(name)
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
                                std_sub_name = standardize(sub_name)
                                if std_sub_name:
                                    result[current_category][current_country][std_name].append(std_sub_name)

        return result