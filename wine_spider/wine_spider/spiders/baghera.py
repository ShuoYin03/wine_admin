import os
import json
import scrapy
import dotenv
from dateutil import parser
from wine_spider.items import AuctionItem, LotItem
from wine_spider.services.baghera_client import BagheraClient
from wine_spider.helpers import (
    extract_year
)
from wine_spider.exceptions import (
    NoPreDefinedVolumeIdentifierException
)
from collections import defaultdict

from wine_spider.helpers import make_serializable
from wine_spider.helpers import unit_format_to_volume
from wine_spider.helpers import filter_to_params
from wine_spider.helpers import region_to_country
from wine_spider.services import PDFParser

dotenv.load_dotenv()
FULL_FETCH = os.getenv("FULL_FETCH")

class BagheraSpider(scrapy.Spider):
    name = "baghera_spider"
    allowed_domains = [
    ]

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "LOG_FILE": "baghera_log.txt",
        # "JOBDIR": "wine_spider/crawl_state/baghera",
    }

    start_urls = [
        "https://www.bagherawines.auction/en/catalogue/archive"
    ]

    def __init__(self, *args, **kwargs):
        super(BagheraSpider, self).__init__(*args, **kwargs)
        self.baghera_client = BagheraClient()
        self.pdf_parser = PDFParser()

    def parse(self, response):
        auction_links = response.css("div.col-8 a::attr(href)").getall()
        for auction_link in auction_links[1:2]:
            yield scrapy.Request(
                url=self.baghera_client.get_auction_url(auction_link), 
                callback=self.parse_auction_page,
                meta={
                    "original_url": auction_link
                }
            )

            break
        
    def parse_auction_page(self, response):
        original_url = response.meta.get("original_url")
        auction_info = response.css("ul.infos.text-uppercase")
        self.parse_auction(auction_info, response.css("h1::text").get().strip(), response.url)

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
        
        currency = response.css("select.form-control#change_devise option[selected]::text").get()
        lot_htmls = response.css("div#liste_lots div.lot_item")
        for lot_html in lot_htmls:
            lot_info_html = lot_html.css("div.caracteristiques table tbody")
            lot_unit_format = lot_info_html.css("tr:nth-child(1) td:nth-child(1)::text").get()
            lot_unit_format = lot_unit_format.replace(":", "").replace("(S)", "").replace("(s)", "").strip()
            lot_unit = int(lot_info_html.css("tr:nth-child(1) td:nth-child(2) span::text").get())
            
            sequence_external_id = lot_html.css("p.numero.mb0::text").get().strip()
            lot_item = LotItem(
                external_id = lot_html.css("a.lien-lot::attr(href)").get().split("/")[-1],
                auction_id = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")[1],
                lot_name = lot_html.css("h3 span::text").get().strip(),
                unit = lot_unit,
                original_currency = currency,
                low_estimate = int(lot_info_html.css("tr:nth-child(2) span.estimation_basse_ori::text").get().replace(" ", "")),
                high_estimate = int(lot_info_html.css("tr:nth-child(3) span.estimation_haute_ori::text").get().replace(" ", "")),
                success = True,
                url = lot_html.css("a.lien-lot::attr(href)").get(),
            )

            try:
                lot_item['volume'] = lot_unit * unit_format_to_volume(lot_unit_format)
            except NoPreDefinedVolumeIdentifierException as e:
                self.logger.error(f"Volume identifier not found for {lot_unit_format}: {e}")
                lot_item['success'] = False

            lots[sequence_external_id]["lot_item"] = lot_item
            lots[sequence_external_id]["lot_detail_info"]["vintage"].append(
                extract_year(lot_item['lot_name'])
            )
            lots[sequence_external_id]["lot_detail_info"]["unit_format"].append(
                lot_unit_format
            )
            
        search_bar_html = response.css("div.searchbar")
        filter_htmls = search_bar_html.css("div.checkboxes.collapse")
        filters = defaultdict(list)
        for filter_html in filter_htmls:
            filter = filter_to_params(filter_html.css("::attr(id)").get())
            if not filter:
                continue
            filter_search_param = filter_html.css("::attr(id)").get().split("-")[-1]
            labels = filter_html.css("label::text").getall()

            filters[filter_search_param] = labels

        for filter in filters.keys():
            if filters[filter]:
                data = filters[filter].pop(0)
                yield scrapy.Request(
                    url=self.baghera_client.get_filtered_auction_url(original_url, filter, data), 
                    callback=self.parse_filters, 
                    meta={
                        "original_url": original_url,
                        "current_filter": filter,
                        "current_data": data,
                        "filters": filters,
                        "lots": lots,
                    }
                )

            break
    
    def parse_filters(self, response):
        original_url = response.meta.get("original_url")
        current_filter = response.meta.get("current_filter")
        current_data = response.meta.get("current_data")
        filters = response.meta.get("filters")
        lots = response.meta.get("lots")

        lot_htmls = response.css("div#liste_lots div.lot_item")
        for lot_html in lot_htmls:
            sequence_external_id = lot_html.css("p.numero.mb0::text").get().strip()
            # external_id = lot_html.css("a.lien-lot::attr(href)").get().split("/")[-1]
            if sequence_external_id not in lots:
                print(f"Lot {sequence_external_id} not found in lots dictionary.")
                print(f"Current filter: {current_filter}, Current data: {current_data}")
            else:
                print(f"Processing lot {sequence_external_id} with filter {current_filter} and data {current_data}")
                self.add_data(current_filter, current_data, lots[sequence_external_id]["lot_item"], lots[sequence_external_id]["lot_detail_info"])
        
        trigered = False
        for filter in filters.keys():
            if filters[filter]:
                trigered = True
                data = filters[filter].pop(0)
                yield scrapy.Request(
                    url=self.baghera_client.get_filtered_auction_url(original_url, filter, data), 
                    callback=self.parse_filters, 
                    meta={
                        "original_url": original_url,
                        "current_filter": filter,
                        "current_data": data,
                        "filters": filters,
                        "lots": lots,
                    }
                )

            if trigered:
                break

        if not trigered:
            pdf_url = response.xpath('//a[@class="lien-noir" and @target="_blank" and contains(text(), "Sale results")]/@href').get()
            if pdf_url:
                yield scrapy.Request(
                    url=pdf_url,
                    callback=self.parse_pdf,
                    meta={
                        "lots": lots,
                    }
                )
            else:
                self.logger.info(f"No sales PDF found for auction at {original_url}.")
                self.yield_items(lots)

    def parse_pdf(self, response):
        lots = response.meta.get("lots")

        content = self.pdf_parser.parse(response.body)
        lines = content.splitlines()

        for line in lines:
            if line[0].isdigit():
                sequence_external_id = line.split(" ")[0]
                if sequence_external_id in lots:
                    price = line.split(" ")[-1]
                    price = price.replace("'", "")
                    lots[sequence_external_id]["lot_item"]["end_price"] = price
                else:
                    print(f"Lot {sequence_external_id} not found in lots dictionary while parsing PDF.")

        self.yield_items(lots)

    def yield_items(self, lots):
        lots_json = make_serializable(lots)
        with open("baghera_lots.json", "w") as f:
            json.dump(lots_json, f, indent=4)

    def parse_auction(self, auction_info, auction_title, url):
        auction_id = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")[1]
        auction_time_and_location = auction_info.css("li:nth-child(2) span::text").get().strip()
        auction_time = auction_time_and_location.split(" (")[0].strip()
        auction_time = parser.parse(auction_time)
        auction_location = auction_time_and_location.split(" (")[1].replace(")", "").strip()

        auction_item = AuctionItem(
            external_id=auction_id,
            auction_title=auction_title,
            auction_house="Baghera",
            city=auction_location.split("/")[1].strip().title(),
            continent=auction_location.split("/")[0].strip().title(),
            start_date=auction_time,
            year=auction_time.year,
            quarter=(auction_time.month - 1) // 3 + 1,
            auction_type="PAST",
            url=url,
        )

        # yield auction_item
    
    def add_data(self, filter, data, lot_item, lot_detail_info):
        try:
            if filter == "lot_producer":
                lot_detail_info[filter].append(data)
            elif filter == "region":
                lot_item["region"] = data
                lot_item["country"] = region_to_country(data)
            elif filter == "wine_colour":
                lot_detail_info[filter].append(data)
            elif filter == "lot_type":
                if "lot_type" not in lot_item:
                    lot_item["lot_type"] = [data]
                else:
                    lot_item["lot_type"].append(data)
        except Exception as e:
            print(filter, data, lot_item, lot_detail_info)