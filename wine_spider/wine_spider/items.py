import scrapy

class AuctionItem:
    def __init__(self, id=None, auction_title=None, auction_house=None, city=None, continent=None, 
                 start_date=None, end_date=None, year=None, quarter=None, auction_type=None):
        self.id = id
        self.auction_title = auction_title
        self.auction_house = auction_house
        self.city = city
        self.continent = continent
        self.start_date = start_date
        self.end_date = end_date
        self.year = year
        self.quarter = quarter
        self.auction_type = auction_type

    def to_dict(self):
        return {
            "id": self.id,
            "auction_title": self.auction_title,
            "auction_house": self.auction_house,
            "city": self.city,
            "continent": self.continent,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "year": self.year,
            "quarter": self.quarter,
            "auction_type": self.auction_type
        }

class AuctionSalesItem:
    def __init__(self, id=None, lots=None, sold=None, currency=None, total_low_estimate=None, total_high_estimate=None, 
                 total_sales=None, volumn_sold=None, value_sold=None, top_lot=None, sale_type=None, single_cellar=None, 
                 exch=None):
        self.id = id
        self.lots = lots
        self.sold = sold
        self.currency = currency
        self.total_low_estimate = total_low_estimate
        self.total_high_estimate = total_high_estimate
        self.total_sales = total_sales
        self.volumn_sold = volumn_sold
        self.value_sold = value_sold
        self.top_lot = top_lot
        self.sale_type = sale_type
        self.single_cellar = single_cellar
        self.exch = exch

    def to_dict(self):
        return {
            "id": self.id,
            "lots": self.lots,
            "sold": self.sold,
            "currency": self.currency,
            "total_low_estimate": self.total_low_estimate,
            "total_high_estimate": self.total_high_estimate,
            "total_sales": self.total_sales,
            "volumn_sold": self.volumn_sold,
            "value_sold": self.value_sold,
            "top_lot": self.top_lot,
            "sale_type": self.sale_type,
            "single_cellar": self.single_cellar,
            "exch": self.exch
        }

class LotItem:
    def __init__(self, id=None, lot_producer=None, wine_name=None, vintage=None, unit_format=None, unit=None, 
                 currency=None, start_price=None, end_price=None, sold=None, region=None, country=None):
        self.id = id
        self.lot_producer = lot_producer
        self.wine_name = wine_name
        self.vintage = vintage
        self.unit_format = unit_format
        self.unit = unit
        self.currency = currency
        self.start_price = start_price
        self.end_price = end_price
        self.sold = sold
        self.region = region
        self.country = country
    
    def to_dict(self):
        return {
            "id": self.id,
            "lot_producer": self.lot_producer,
            "wine_name": self.wine_name,
            "vintage": self.vintage,
            "unit_format": self.unit_format,
            "unit": self.unit,
            "currency": self.currency,
            "start_price": self.start_price,
            "end_price": self.end_price,
            "sold": self.sold,
            "region": self.region,
            "country": self.country
        }
        
