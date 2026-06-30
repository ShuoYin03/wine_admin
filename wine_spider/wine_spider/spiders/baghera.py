import os
import re
import scrapy
from collections import defaultdict
from dateutil import parser
from wine_spider.items import AuctionItem, LotItem, LotDetailItem
from wine_spider.spiders.base_auction_spider import BaseAuctionSpider
from wine_spider.services.baghera_client import BagheraClient
from wine_spider.helpers import (
    extract_year, unit_format_to_volume, convert_to_volume, filter_to_params,
    region_to_country, expand_to_lot_items, extract_lot_part,
    build_lot_external_id,
)
from wine_spider.exceptions import NoPreDefinedVolumeIdentifierException
from wine_spider.services import PDFParser
from shared.database.auctions_client import AuctionsClient


class BagheraSpider(BaseAuctionSpider):
    name = "baghera_spider"
    allowed_domains = []
    handle_httpstatus_list = [400, 403, 429, 500, 502, 503, 504]

    custom_settings = BaseAuctionSpider.build_custom_settings(
        "baghera.log",
        extra={
            # "JOBDIR": "wine_spider/crawl_state/baghera",
        },
    )

    start_urls = [
        "https://www.bagherawines.auction/en/catalogue/archive"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.baghera_client = BagheraClient()
        self.pdf_parser = PDFParser()
        self.auction_client = AuctionsClient()
        self.backfill_auction_ids = {
            auction_id.strip()
            for auction_id in os.getenv("BACKFILL_AUCTION_IDS", "").split(",")
            if auction_id.strip()
        }

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
        auction_id_text_split = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")
        auction_id = "".join(auction_id_text_split[1:])
        if self.backfill_auction_ids and auction_id not in self.backfill_auction_ids:
            self.logger.debug(f"Auction {auction_id} is not in BACKFILL_AUCTION_IDS. Skipping...")
            return

        if self.check_auction_exists(auction_id, self.auction_client):
            return
        
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
            source_lot_id = lot_html.css("a.lien-lot::attr(href)").get().split("/")[-1]
            lot_name = lot_html.css("h3 span::text").get()
            lot_name = lot_name.strip() if lot_name and lot_name.strip() else f"Lot {sequence_external_id}"
            lot_item = LotItem(
                external_id = build_lot_external_id(auction_id, source_lot_id),
                auction_id = auction_id,
                lot_name = lot_name,
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

        filter_request = self.next_filter_request(
            original_url=original_url,
            filters=filters,
            lots=lots,
            processed_lots=processed_lots,
            pdf_url=pdf_url,
        )
        if filter_request:
            yield filter_request
        else:
            yield from self.finalize_filtered_lots(
                original_url=original_url,
                lots=lots,
                pdf_url=pdf_url,
            )
    
    def parse_filters(self, response):
        original_url = response.meta.get("original_url")
        current_filter = response.meta.get("current_filter")
        current_data = response.meta.get("current_data")
        filters = response.meta.get("filters")
        lots = response.meta.get("lots")
        processed_lots = response.meta.get("processed_lots")
        pdf_url = response.meta.get("pdf_url")

        if response.status >= 400:
            self.logger.warning(
                "Baghera filter returned HTTP %s for %s. Continuing without this filter.",
                response.status,
                response.url,
            )
            yield from self.continue_filter_chain(response.meta)
            return

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
        
        response_pdf_url = response.xpath('//a[@class="lien-noir" and @target="_blank" and (contains(text(), "Sale results") or contains(text(), "Sale result"))]/@href').get()
        response.meta["pdf_url"] = response_pdf_url or pdf_url
        yield from self.continue_filter_chain(response.meta)

    def parse_filter_error(self, failure):
        request = failure.request
        self.logger.warning(
            "Baghera filter request failed for %s: %s. Continuing without this filter.",
            request.url,
            failure.getErrorMessage(),
        )
        yield from self.continue_filter_chain(request.meta)

    def continue_filter_chain(self, meta):
        request = self.next_filter_request(
            original_url=meta.get("original_url"),
            filters=meta.get("filters"),
            lots=meta.get("lots"),
            processed_lots=meta.get("processed_lots"),
            pdf_url=meta.get("pdf_url"),
        )
        if request:
            yield request
            return

        yield from self.finalize_filtered_lots(
            original_url=meta.get("original_url"),
            lots=meta.get("lots"),
            pdf_url=meta.get("pdf_url"),
        )

    def next_filter_request(self, original_url, filters, lots, processed_lots, pdf_url=None):
        for filter in filters.keys():
            if filters[filter]:
                search_value, data = filters[filter].pop(0)
                return scrapy.Request(
                    url=self.baghera_client.get_filtered_auction_url(original_url, filter, search_value),
                    callback=self.parse_filters,
                    errback=self.parse_filter_error,
                    dont_filter=True,
                    meta={
                        "original_url": original_url,
                        "current_filter": filter,
                        "current_data": data,
                        "filters": filters,
                        "lots": lots,
                        "processed_lots": processed_lots,
                        "pdf_url": pdf_url,
                        "handle_httpstatus_list": [400, 403, 429, 500, 502, 503, 504],
                        "dont_retry": True,
                    }
                )

        return None

    def finalize_filtered_lots(self, original_url, lots, pdf_url=None):
        detail_sequence_ids = self.detail_fallback_sequence_ids(lots)
        detail_request = self.next_detail_fallback_request(
            original_url=original_url,
            lots=lots,
            pending_detail_sequence_ids=detail_sequence_ids,
            pdf_url=pdf_url,
        )
        if detail_request:
            yield detail_request
            return

        yield from self.finalize_lots_with_pdf(original_url, lots, pdf_url=pdf_url)

    def finalize_lots_with_pdf(self, original_url, lots, pdf_url=None):
        if pdf_url:
            yield scrapy.Request(
                url=pdf_url,
                callback=self.parse_pdf,
                dont_filter=True,
                meta={
                    "lots": lots,
                }
            )
        else:
            self.logger.info(f"No sales PDF found for auction at {original_url}.")
            yield from self.yield_items(lots)

    def detail_fallback_sequence_ids(self, lots):
        sequence_ids = []
        for sequence_external_id, lot in (lots or {}).items():
            if self.needs_detail_fallback(lot):
                sequence_ids.append(sequence_external_id)
        return sequence_ids

    def needs_detail_fallback(self, lot):
        lot_item = (lot or {}).get("lot_item")
        lot_detail_info = (lot or {}).get("lot_detail_info") or {}
        if not lot_item or not lot_item.get("url"):
            return False

        has_producer = any(
            str(value).strip()
            for value in lot_detail_info.get("lot_producer", [])
            if value is not None
        )
        has_wine_colour = any(
            str(value).strip()
            for value in lot_detail_info.get("wine_colour", [])
            if value is not None
        )
        return not (has_producer and has_wine_colour)

    def next_detail_fallback_request(
        self,
        original_url,
        lots,
        pending_detail_sequence_ids,
        pdf_url=None,
    ):
        while pending_detail_sequence_ids:
            sequence_external_id = pending_detail_sequence_ids.pop(0)
            lot = (lots or {}).get(sequence_external_id)
            lot_item = (lot or {}).get("lot_item")
            lot_url = lot_item.get("url") if lot_item else None
            if not lot_url:
                continue

            return scrapy.Request(
                url=lot_url,
                callback=self.parse_detail_fallback,
                errback=self.parse_detail_fallback_error,
                dont_filter=True,
                meta={
                    "original_url": original_url,
                    "lots": lots,
                    "sequence_external_id": sequence_external_id,
                    "pending_detail_sequence_ids": pending_detail_sequence_ids,
                    "pdf_url": pdf_url,
                    "handle_httpstatus_list": [400, 403, 429, 500, 502, 503, 504],
                    "dont_retry": True,
                },
            )
        return None

    def parse_detail_fallback(self, response):
        sequence_external_id = response.meta.get("sequence_external_id")
        lots = response.meta.get("lots")
        lot = (lots or {}).get(sequence_external_id)
        lot_item = (lot or {}).get("lot_item")

        if response.status >= 400:
            self.logger.warning(
                "Baghera detail fallback returned HTTP %s for lot %s at %s.",
                response.status,
                sequence_external_id,
                response.url,
            )
            yield from self.continue_detail_fallback_chain(response.meta)
            return

        if lot_item:
            lot_detail_items = self.parse_lot_detail_items_from_page(response, lot_item)
            if lot_detail_items:
                self.apply_lot_detail_items(lot["lot_detail_info"], lot_detail_items)
            else:
                self.logger.warning(
                    "Baghera detail fallback found no detail fields for lot %s.",
                    sequence_external_id,
                )

        yield from self.continue_detail_fallback_chain(response.meta)

    def parse_detail_fallback_error(self, failure):
        request = failure.request
        self.logger.warning(
            "Baghera detail fallback request failed for %s: %s. Continuing.",
            request.url,
            failure.getErrorMessage(),
        )
        yield from self.continue_detail_fallback_chain(request.meta)

    def continue_detail_fallback_chain(self, meta):
        detail_request = self.next_detail_fallback_request(
            original_url=meta.get("original_url"),
            lots=meta.get("lots"),
            pending_detail_sequence_ids=meta.get("pending_detail_sequence_ids") or [],
            pdf_url=meta.get("pdf_url"),
        )
        if detail_request:
            yield detail_request
            return

        yield from self.finalize_lots_with_pdf(
            original_url=meta.get("original_url"),
            lots=meta.get("lots"),
            pdf_url=meta.get("pdf_url"),
        )

    def apply_lot_detail_items(self, lot_detail_info, lot_detail_items):
        field_map = {
            "lot_producer": "lot_producer",
            "vintage": "vintage",
            "unit_format": "unit_format",
            "wine_colour": "wine_colour",
        }
        for detail_key, item_key in field_map.items():
            values = [
                lot_detail_item.get(item_key)
                for lot_detail_item in lot_detail_items
                if lot_detail_item.get(item_key)
            ]
            if values:
                lot_detail_info[detail_key] = values

    def parse_label_value_details(self, response):
        details = {}
        for label_html in response.css(".information_label"):
            label = label_html.xpath("normalize-space(.)").get()
            value = label_html.xpath("normalize-space(following-sibling::*[1])").get()
            if label and value:
                details[label.strip().lower()] = value.strip()
        return details

    def normalize_unit_format(self, unit_format):
        if not unit_format:
            return None
        normalized = re.sub(r'\([^)]*\)', '', unit_format).replace(":", "").lower().strip()
        if normalized in {"mganum", "mganums"}:
            return "magnum"
        return normalized

    def yield_single_lot_items(self, lot_item, lot_detail_items, sequence_external_id, pdf_url=None):
        if pdf_url:
            yield scrapy.Request(
                url=pdf_url,
                callback=self.parse_pdf_for_single_lot,
                dont_filter=True,
                meta={
                    "lot_item": lot_item,
                    "lot_detail_items": lot_detail_items,
                    "sequence_external_id": sequence_external_id,
                }
            )
        else:
            yield lot_item
            for lot_detail_item in lot_detail_items:
                yield lot_detail_item

    def parse_flat_lot_detail_items(self, response, lot_item):
        details = self.parse_label_value_details(response)
        if not details:
            return []

        capacity = self.normalize_unit_format(details.get("capacity"))
        format_label = self.normalize_unit_format(details.get("format"))
        unit_format = capacity or format_label
        quantity_text = details.get("quantity")
        quantity = int(quantity_text) if quantity_text and quantity_text.isdigit() else lot_item.get("unit") or 1

        if unit_format:
            volume_per_unit = convert_to_volume(unit_format)
            if volume_per_unit is None:
                try:
                    volume_per_unit = unit_format_to_volume(unit_format)
                except NoPreDefinedVolumeIdentifierException as e:
                    self.logger.error(e)
            if volume_per_unit is not None:
                lot_item["volume"] = quantity * volume_per_unit

        nature = details.get("nature")
        lot_item["lot_type"] = [nature] if nature else []
        lot_item["region"] = details.get("area")
        lot_item["country"] = details.get("country of origin")
        lot_item["sub_region"] = details.get("subdivision")

        if not any(details.get(key) for key in ("producer", "vintage", "format", "type")):
            return []

        return [
            LotDetailItem(
                lot_id=lot_item["external_id"],
                lot_producer=details.get("producer"),
                vintage=details.get("vintage"),
                unit_format=unit_format,
                wine_colour=details.get("type"),
            )
        ]

    def parse_lot_detail_items_from_page(self, response, lot_item):
        lot_detail_information_section = response.css("span.ecart.style7").get()
        if not lot_detail_information_section:
            return self.parse_flat_lot_detail_items(response, lot_item)

        return self.parse_mixed_lot_detail_items(response, lot_item)

    def parse_mixed_lot_detail_items(self, response, lot_item):
        first_run = True
        lot_detail_items = []
        volume = 0
        lot_type = None
        region = None
        sub_region = None
        country = None
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

        return lot_detail_items

    def parse_lot_page(self, response):
        lot_item = response.meta.get("lot_item")
        sequence_external_id = response.meta.get("sequence_external_id")
        pdf_url = response.meta.get("pdf_url")

        lot_detail_items = self.parse_lot_detail_items_from_page(response, lot_item)
        if not lot_detail_items:
            self.logger.warning(f"Lot detail information section not found for lot {sequence_external_id}.")

        if not pdf_url:
            self.logger.info(f"No sales PDF found for lot {sequence_external_id}.")
        yield from self.yield_single_lot_items(
            lot_item,
            lot_detail_items,
            sequence_external_id,
            pdf_url=pdf_url,
        )

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

        yield from self.yield_items(lots)

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
        auction_id_text_split = auction_info.css("li:nth-child(4)::text").get().strip().split(" ")
        auction_id = "".join(auction_id_text_split[1:])
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
