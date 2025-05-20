from .base_database_client import BaseDatabaseClient
from .model import LotModel, AuctionModel, LotItemModel
from sqlalchemy import func

class LotsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotModel, db_instance=db_instance)
        
    def query_lots_with_auction(self, filters=None, order_by=None, limit=None, offset=None, return_count=False):
        with self.session_scope() as session:
            lots = LotModel
            auctions = AuctionModel
            table_map = {"lots": lots, "auctions": auctions}

            query = session.query(lots)
            query = query.select_from(lots).join(lots.auction).add_entity(auctions)

            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            count = None
            if return_count:
                count = self.get_table_count(session, filters=filters, table_map=table_map)

            results = query.all()
            data = [
                {
                    **lot.model_to_dict(),
                    "auction": auction.model_to_dict(),
                }
                for lot, auction in results
            ]
            
            return (data, count) if return_count else (data, None)
        
    def query_lots_with_items_and_auction(self, filters=None, order_by=None, limit=None, offset=None, return_count=False):
        with self.session_scope() as session:
            lots = LotModel
            auctions = AuctionModel
            items = LotItemModel
            table_map = {"lots": lots, "auctions": auctions, "items": items}

            query = session.query(lots).join(lots.auction).add_entity(auctions).join(items).add_entity(items)

            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)
            
            count = None
            if return_count:
                count = self.get_table_count(session, filters=filters, table_map=table_map)

            results = query.all()
            data = [
                {
                    **lot.model_to_dict(),
                    "lot_items": item.model_to_dict(),
                    "auction" : auction.model_to_dict(),
                }
                for lot, auction, item in results
            ]

            return (data, count) if return_count else (data, None)