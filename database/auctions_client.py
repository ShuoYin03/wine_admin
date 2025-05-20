from .base_database_client import BaseDatabaseClient
from .model import AuctionModel, AuctionSalesModel, LotModel

class AuctionsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(AuctionModel, db_instance=db_instance)
    
    def query_single_auction(self, auction_id):
        with self.session_scope() as session:
            auction = session.query(AuctionModel).filter_by(external_id=auction_id).first()
            if not auction:
                return None

            return {
                **auction.model_to_dict(),
                "sales": auction.auction_sales.model_to_dict() if auction.auction_sales else None,
                "lots": [lot.model_to_dict() for lot in auction.lots]
            }
        
    def query_auctions_with_sales(self, filters=None, order_by=None, limit=None, offset=None, return_count=False):
        with self.session_scope() as session:
            auctions = AuctionModel
            sales = AuctionSalesModel
            table_map = {"auctions": auctions, "sales": sales}

            query = session.query(auctions).join(sales, auctions.external_id == sales.auction_id).add_entity(sales)
            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            count = None
            if return_count:
                count = self.get_table_count(session, filters=filters, table_map=table_map)

            results = query.all()
            data = [
                {
                    **auction.model_to_dict(),
                    "sales": sales.model_to_dict()
                }
                for auction, sales in results
            ]
            
            return (data, count) if return_count else (data, None)