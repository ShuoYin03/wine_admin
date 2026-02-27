from .base_database_client import BaseDatabaseClient
from shared.database.models.auction_sales_db import AuctionSalesModel
from shared.database.models.auction_db import AuctionModel

class AuctionSalesClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(AuctionSalesModel, db_instance=db_instance)

    def get_by_external_id(self, auction_id):
        with self.session_scope() as session:
            auction_sale = session.query(self.model).filter_by(auction_id=auction_id).first()
            if auction_sale:
                return auction_sale.model_to_dict()
            return None

    def get_by_auction_house(self, auction_house):
        with self.session_scope() as session:
            return (
                session.query(self.model)
                .join(AuctionModel, self.model.auction_id == AuctionModel.external_id)
                .filter(AuctionModel.auction_house == auction_house)
                .all()
            )

    def upsert_by_external_id(self, data_dict):
        with self.session_scope() as session:
            instance = session.query(self.model).filter_by(auction_id=data_dict.get("auction_id")).first()
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)