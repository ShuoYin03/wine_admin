import scrapy
from datetime import datetime, date

class AuctionItem(scrapy.Item):
    external_id = scrapy.Field()
    auction_title = scrapy.Field()
    auction_house = scrapy.Field()
    city = scrapy.Field()
    continent = scrapy.Field()
    start_date = scrapy.Field()
    end_date = scrapy.Field()
    year = scrapy.Field()
    quarter = scrapy.Field()
    auction_type = scrapy.Field()
    url = scrapy.Field()

class LotItem(scrapy.Item):
    external_id = scrapy.Field()
    auction_id = scrapy.Field()
    lot_name = scrapy.Field()
    lot_type = scrapy.Field()
    volume = scrapy.Field()
    unit = scrapy.Field()
    original_currency = scrapy.Field()
    start_price = scrapy.Field()
    end_price = scrapy.Field()
    low_estimate = scrapy.Field()
    high_estimate = scrapy.Field()
    sold = scrapy.Field()
    sold_date = scrapy.Field()
    region = scrapy.Field()
    sub_region = scrapy.Field()
    country = scrapy.Field()
    success = scrapy.Field()
    url = scrapy.Field()

    def to_serializable_dict(self):
        d = dict(self)
        if isinstance(d.get("sold_date"), (datetime, date)):
            d["sold_date"] = d["sold_date"].isoformat()
        return d

class LotDetailItem(scrapy.Item):
    lot_id = scrapy.Field()
    lot_producer = scrapy.Field()
    vintage = scrapy.Field()
    unit_format = scrapy.Field()
    wine_colour = scrapy.Field()

class AuctionSalesItem(scrapy.Item):
    id = scrapy.Field()
    auction_id = scrapy.Field()
    lots = scrapy.Field()
    sold = scrapy.Field()
    currency = scrapy.Field()
    total_low_estimate = scrapy.Field()
    total_high_estimate = scrapy.Field()
    total_sales = scrapy.Field()
    volume_sold = scrapy.Field()
    value_sold = scrapy.Field()
    top_lot = scrapy.Field()
    sale_type = scrapy.Field()
    single_cellar = scrapy.Field()
    ex_ch = scrapy.Field()

class LwinMatchingItem(scrapy.Item):
    id = scrapy.Field()
    lot_id = scrapy.Field()
    matched = scrapy.Field()
    lwin = scrapy.Field()
    lwin_11 = scrapy.Field()
    match_item = scrapy.Field()
    match_score = scrapy.Field()

class FxRateItem(scrapy.Item):
    rates_from = scrapy.Field()
    rates_to = scrapy.Field()
    rates = scrapy.Field()

class CombinedLotItem(scrapy.Item):
    lot = scrapy.Field()
    lot_items = scrapy.Field()