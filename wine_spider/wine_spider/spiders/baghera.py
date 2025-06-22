import os
import re
import scrapy
import dotenv
from dateutil import parser
from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.services.baghera_client import BagheraClient
from wine_spider.helpers import (
    extract_year
)
from wine_spider.exceptions import (
    NoPreDefinedVolumeIdentifierException
)
from collections import defaultdict
from wine_spider.helpers import unit_format_to_volume
from wine_spider.helpers import filter_to_params
from wine_spider.helpers import region_to_country
from wine_spider.services import PDFParser
from wine_spider.helpers import expand_to_lot_items
from wine_spider.helpers import extract_lot_part

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
        for auction_link in auction_links:
            # if auction_link == "https://www.bagherawines.auction/en/catalogue/voir/82":
            yield scrapy.Request(
                url=self.baghera_client.get_auction_url(auction_link), 
                callback=self.parse_auction_page,
                meta={
                    "original_url": auction_link
                }
            )
        
    def parse_auction_page(self, response):
        original_url = response.meta.get("original_url")
        auction_info = response.css("ul.infos.text-uppercase")
        yield from self.parse_auction(auction_info, response.css("h1::text").get().strip(), response.url)
        pdf_url = response.xpath('//a[@class="lien-noir" and @target="_blank" and contains(text(), "Sale results")]/@href').get()

        lots = defaultdict(
            lambda: {
                "lot_item": None, 
                "lot_detail_info": {
                    k: [] for k in [
                        "lot_producer", 
                        "vintage", 
                        "unit_format", 
                        "wine_colour"
                    ]
                }
            }
        )
        processed_lots = []
        
        currency = response.css("select.form-control#change_devise option[selected]::text").get()
        lot_htmls = response.css("div#liste_lots div.lot_item")
        for lot_html in lot_htmls:
            lot_info_html = lot_html.css("div.caracteristiques table tbody")
            lot_unit_format = lot_info_html.css("tr:nth-child(1) td:nth-child(1)::text").get()

            if "Parcel" in lot_unit_format:
                lot_unit_format = lot_info_html.css("tr:nth-child(2) td:nth-child(1)::text").get()
                lot_unit = int(lot_info_html.css("tr:nth-child(2) td:nth-child(2) span::text").get())
            else:
                lot_unit = int(lot_info_html.css("tr:nth-child(1) td:nth-child(2) span::text").get())

            try:
                lot_unit_format = re.sub(r'\([^)]*\)', '', lot_unit_format).replace(":", "").lower().strip()
            except Exception as e:
                self.logger.error(f"Error processing lot unit format: {e}")
            
            sequence_external_id = lot_html.css("p.numero.mb0::text").get().strip()
            lot_item = LotItem(
                external_id = lot_html.css("a.lien-lot::attr(href)").get().split("/")[-1],
                auction_id = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")[1],
                lot_name = lot_html.css("h3 span::text").get().strip(),
                unit = lot_unit,
                original_currency = currency,
                low_estimate = int(lot_info_html.css("tr:nth-last-child(2) span.estimation_basse_ori::text").get().replace(" ", "")),
                high_estimate = int(lot_info_html.css("tr:nth-last-child(1) span.estimation_haute_ori::text").get().replace(" ", "")),
                success = True,
                url = lot_html.css("a.lien-lot::attr(href)").get(),
            )

            try:
                lot_item['volume'] = lot_unit * unit_format_to_volume(lot_unit_format)
            except NoPreDefinedVolumeIdentifierException as e:
                processed_lots.append(sequence_external_id)

                yield scrapy.Request(
                    url=lot_item['url'],
                    callback=self.parse_lot_page,
                    meta={
                        "lot_item": lot_item,
                        "pdf_url": pdf_url,
                        "sequence_external_id": sequence_external_id,
                    }
                )

                continue

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
            search_value = filter_html.css("label::attr(for)").getall()
            labels = filter_html.css("label::text").getall()

            filters[filter_search_param] = [(search_value[i].split("_")[-1], labels[i]) for i in range(len(search_value))]

        for filter in filters.keys():
            if filters[filter]:
                search_value, data = filters[filter].pop(0)
                yield scrapy.Request(
                    url=self.baghera_client.get_filtered_auction_url(original_url, filter, search_value), 
                    callback=self.parse_filters, 
                    meta={
                        "original_url": original_url,
                        "current_filter": filter,
                        "current_data": data,
                        "filters": filters,
                        "lots": lots,
                        "processed_lots": processed_lots,
                    }
                )

            break
    
    def parse_filters(self, response):
        original_url = response.meta.get("original_url")
        current_filter = response.meta.get("current_filter")
        current_data = response.meta.get("current_data")
        filters = response.meta.get("filters")
        lots = response.meta.get("lots")
        processed_lots = response.meta.get("processed_lots")

        lot_htmls = response.css("div#liste_lots div.lot_item")
        for lot_html in lot_htmls:
            sequence_external_id = lot_html.css("p.numero.mb0::text").get().strip()
            if sequence_external_id not in lots:
                if sequence_external_id not in processed_lots:
                    self.logger.warning(f"Lot {sequence_external_id} not found in lots dictionary.")
            else:
                if sequence_external_id not in processed_lots:
                    try:
                        self.add_data(filter_to_params(current_filter), current_data, lots[sequence_external_id]["lot_item"], lots[sequence_external_id]["lot_detail_info"])
                    except Exception as e:
                        self.logger.error(f"Error adding data for lot {sequence_external_id}: {e}")
                        self.logger.debug(filters)
        
        trigered = False
        for filter in filters.keys():
            if filters[filter]:
                trigered = True
                search_value, data = filters[filter].pop(0)

                yield scrapy.Request(
                    url=self.baghera_client.get_filtered_auction_url(original_url, filter, search_value), 
                    callback=self.parse_filters, 
                    meta={
                        "original_url": original_url,
                        "current_filter": filter,
                        "current_data": data,
                        "filters": filters,
                        "lots": lots,
                        "processed_lots": processed_lots,
                    }
                )
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
                yield from self.yield_items(lots)

    def parse_lot_page(self, response):
        lot_item = response.meta.get("lot_item")
        sequence_external_id = response.meta.get("sequence_external_id")
        pdf_url = response.meta.get("pdf_url")

        lot_detail_information_section = response.css("span.ecart.style7").get()
        if not lot_detail_information_section:
            self.logger.warning(f"Lot detail information section not found for lot {sequence_external_id}.")
            return

        first_run = True
        lot_detail_items = []
        volume = 0
        wine_htmls = response.css("div.row.lot_mixte_item")
        for wine_html in wine_htmls:
            vintage = wine_html.xpath(".//div[@class='information_label' and text()='Vintage']").xpath("following-sibling::*[1]/text()").get()
            producer = wine_html.xpath(".//div[@class='information_label' and text()='Producer']").xpath("following-sibling::*[1]/text()").get()
            format = wine_html.xpath(".//div[@class='information_label' and text()='Format']").xpath("following-sibling::*[1]/text()").get()
            format = re.sub(r'\([^)]*\)', '', format).replace(":", "").lower().strip()
            type = wine_html.xpath(".//div[@class='information_label' and text()='Type']").xpath("following-sibling::*[1]/text()").get()
            quantity = wine_html.xpath(".//div[@class='information_label' and text()='Quantity']").xpath("following-sibling::*[1]/text()").get()

            lot_detail_item = LotDetailItem(
                lot_id=lot_item["external_id"],
                lot_producer=producer,
                vintage=vintage,
                unit_format=format,
                wine_colour=type,
            )

            try:
                volume += int(quantity) * unit_format_to_volume(format)
            except NoPreDefinedVolumeIdentifierException as e:
                self.logger.error(e)

            lot_detail_items.append(lot_detail_item)

            if first_run:
                lot_type = wine_html.xpath(".//div[@class='information_label' and text()='Nature']").xpath("following-sibling::*[1]/text()").get()
                region = wine_html.xpath(".//div[@class='information_label' and text()='Area']").xpath("following-sibling::*[1]/text()").get()
                sub_region = wine_html.xpath(".//div[@class='information_label' and text()='Subdivision']").xpath("following-sibling::*[1]/text()").get()
                country = wine_html.xpath(".//div[@class='information_label' and text()='Country of origin']").xpath("following-sibling::*[1]/text()").get()
                first_run = False

        lot_item["volume"] = volume
        lot_item["lot_type"] = [lot_type] if lot_type else []
        lot_item["region"] = region if region else None
        lot_item["country"] = country if country else None
        lot_item["sub_region"] = sub_region if sub_region else None

        if pdf_url:
            yield scrapy.Request(
                url=pdf_url,
                callback=self.parse_pdf_for_single_lot,
                meta={
                    "lot_item": lot_item,
                    "lot_detail_items": lot_detail_items,
                    "sequence_external_id": sequence_external_id,
                }
            )
        else:
            self.logger.info(f"No sales PDF found for lot {sequence_external_id}.")
            yield lot_item
            for lot_detail_item in lot_detail_items:
                yield lot_detail_item

    def parse_pdf_for_single_lot(self, response):
        lot_item = response.meta.get("lot_item")
        lot_detail_items = response.meta.get("lot_detail_items")
        sequence_external_id = response.meta.get("sequence_external_id")

        content = self.pdf_parser.parse(response.body)
        lines = content.splitlines()

        for line in lines:
            if line.startswith(sequence_external_id):
                processed_line = extract_lot_part(line)
                price = processed_line.split(" ")[-1]
                price = price.replace("'", "")
                if price.isdigit() and int(price) > 0:
                    lot_item["end_price"] = int(price)
                    lot_item["sold"] = True
                break
        
        yield lot_item
        for lot_detail_item in lot_detail_items:
            yield lot_detail_item

    def parse_pdf(self, response):
        lots = response.meta.get("lots")

        content = self.pdf_parser.parse(response.body)
        lines = content.splitlines()

        next_line_number = 1
        for line in lines:
            if line[0].isdigit():
                match = re.match(r"^(\d+)", line)
                if match.group(1).isdigit() and int(match.group(1)) != next_line_number:
                    next_line_number += 1
                    continue
                processed_line = extract_lot_part(line)
                sequence_external_id = processed_line.split(" ")[0]
                if sequence_external_id in lots:
                    price = processed_line.split(" ")[-1]
                    price = price.replace("'", "")
                    lots[sequence_external_id]["lot_item"]["end_price"] = price
                else:
                    self.logger.warning(f"Lot {sequence_external_id} not found in lots dictionary while parsing PDF.")
            next_line_number += 1

        self.yield_items(lots)

    def yield_items(self, lots):
        for lot in lots.values():
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

    def parse_auction(self, auction_info, auction_title, url):
        auction_id = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")[1]
        auction_time_and_location = auction_info.css("li:nth-child(2) span::text").get().strip()
        auction_time = auction_time_and_location.split(" (")[0].strip()
        auction_time = parser.parse(auction_time)
        if "(" in auction_time_and_location and ")" in auction_time_and_location:
            auction_location = auction_time_and_location.split(" (")[1].replace(")", "").strip()
            city = auction_location.split("/")[1].strip().title()
            continent = auction_location.split("/")[0].strip().title()
        else:
            city = continent = None

        auction_item = AuctionItem(
            external_id=auction_id,
            auction_title=auction_title,
            auction_house="Baghera",
            city=city,
            continent=continent,
            start_date=auction_time,
            year=auction_time.year,
            quarter=(auction_time.month - 1) // 3 + 1,
            auction_type="PAST",
            url=url,
        )

        yield auction_item
    
    def add_data(self, filter, data, lot_item, lot_detail_info):
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