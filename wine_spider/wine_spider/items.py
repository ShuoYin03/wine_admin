import scrapy

class AuctionItem(scrapy.Item):
    id = scrapy.Field()
    auction_title = scrapy.Field()
    auction_house = scrapy.Field()
    city = scrapy.Field()
    continent = scrapy.Field()
    start_date = scrapy.Field()
    end_date = scrapy.Field()
    year = scrapy.Field()
    quarter = scrapy.Field()
    auction_type = scrapy.Field()

class AuctionSalesItem(scrapy.Item):
    id = scrapy.Field() 
    lots = scrapy.Field()
    sold = scrapy.Field()
    currency = scrapy.Field()
    total_low_estimate = scrapy.Field()
    total_high_estimate = scrapy.Field()
    total_sales = scrapy.Field()
    volumn_sold = scrapy.Field()
    value_sold = scrapy.Field()
    top_lot = scrapy.Field()
    sale_type = scrapy.Field()
    single_cellar = scrapy.Field()
    exch = scrapy.Field()

class LotItem(scrapy.Item):
    id = scrapy.Field()
    auction_id = scrapy.Field()
    lot_producer = scrapy.Field()
    wine_name = scrapy.Field()
    vintage = scrapy.Field()
    unit_format = scrapy.Field()
    unit = scrapy.Field()
    currency = scrapy.Field()
    start_price = scrapy.Field()
    end_price = scrapy.Field()
    low_estimate = scrapy.Field()
    high_estimate = scrapy.Field()
    sold = scrapy.Field()
    region = scrapy.Field()
    country = scrapy.Field()


# AuctionSales:
# auctionId
# numOfLots
# sold
# currency
# totalLowEstimate
# totalHighEstimate
# totalSales
# volumeSold
# valueSold
# topLot

# SingleCellar


# Lots:
# lotId
# auctionId
# Winery
# wineName
# vintage
# format
# unit
# currency

# sold
# region
# country


