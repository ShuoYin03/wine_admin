import csv
from shared.database.models.auction_db import AuctionModel
from shared.database.models.auction_sales_db import AuctionSalesModel
from shared.database.models.lot_db import LotModel
from shared.database.models.lot_item_db import LotItemModel
from shared.database.models.lwin_matching_db import LwinMatchingModel
from .base_database_client import BaseDatabaseClient

class DataExportClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotModel, db_instance=db_instance)

    def export_lots_with_items_by_house(self, auction_house: str, start_date=None, end_date=None):
        with self.session_scope() as session:
            query = (
                session.query(LotModel, LotItemModel, AuctionModel, LwinMatchingModel)
                .join(AuctionModel, LotModel.auction_id == AuctionModel.external_id)
                .outerjoin(LotItemModel, LotModel.external_id == LotItemModel.lot_id)
                .outerjoin(LwinMatchingModel, LotItemModel.id == LwinMatchingModel.lot_id)
                .filter(AuctionModel.auction_house == auction_house)
            )

            if start_date:
                query = query.filter(AuctionModel.start_date >= start_date)
            if end_date:
                query = query.filter(AuctionModel.end_date <= end_date)

            rows = query.all()

            data = []
            for lot, lot_item, auction, lwin in rows:

                data.append({
                    "id": lot.id,
                    "name": lot.lot_name,
                    "type": lot.lot_type,
                    "lwin_7": lwin.lwin if lwin else None,
                    "lwin_11": lwin.lwin_11 if lwin else None,
                    "volume": lot.volume,
                    "unit": lot.unit,
                    "original_currency": lot.original_currency,
                    "start_price": lot.start_price,
                    "end_price": lot.end_price,
                    "low_estimate": lot.low_estimate,
                    "high_estimate": lot.high_estimate,
                    "sold": lot.sold,
                    "sold_date": lot.sold_date,
                    "region": lot.region,
                    "sub_region": lot.sub_region,
                    "country": lot.country,
                    "url": lot.url,
                    "item_producer": lot_item.lot_producer if lot_item else None,
                    "item_vintage": lot_item.vintage if lot_item else None,
                    "item_unit_format": lot_item.unit_format if lot_item else None,
                    "item_wine_colour": lot_item.wine_colour if lot_item else None,
                    "auction_title": auction.auction_title,
                    "auction_house": auction.auction_house,
                    "auction_city": auction.city,
                    "auction_continent": auction.continent,
                    "auction_start_date": auction.start_date,
                    "auction_end_date": auction.end_date,
                    "auction_year": auction.year,
                    "auction_quarter": auction.quarter,
                    "auction_url": auction.url
                })

            return data

    def export_auctions_by_house(self, auction_house: str, start_date=None, end_date=None):
        with self.session_scope() as session:
            query = (
                session.query(AuctionModel, AuctionSalesModel)
                .outerjoin(AuctionSalesModel, AuctionModel.external_id == AuctionSalesModel.auction_id)
                .filter(AuctionModel.auction_house == auction_house)
            )

            if start_date:
                query = query.filter(AuctionModel.start_date >= start_date)
            if end_date:
                query = query.filter(AuctionModel.end_date <= end_date)

            rows = query.all()

            data = []
            for auction, sales in rows:
                data.append({
                    "id": auction.id,
                    "title": auction.auction_title,
                    "house": auction.auction_house,
                    "city": auction.city,
                    "continent": auction.continent,
                    "start_date": auction.start_date,
                    "end_date": auction.end_date,
                    "year": auction.year,
                    "quarter": auction.quarter,
                    "lots": sales.lots if sales else None,
                    "sold": sales.sold if sales else None,
                    "currency": sales.currency if sales else None,
                    "total_low_estimate": sales.total_low_estimate if sales else None,
                    "total_high_estimate": sales.total_high_estimate if sales else None,
                    "total_sales": sales.total_sales if sales else None,
                    "volume_sold": sales.volume_sold if sales else None,
                    "top_lot": sales.top_lot if sales else None,
                    "single_cellar": sales.single_cellar if sales else None,
                    "url": auction.url
                })

            return data