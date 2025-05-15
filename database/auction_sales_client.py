from .base_database_client import BaseDatabaseClient
from .model import AuctionSalesModel

class AuctionSalesClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(AuctionSalesModel, db_instance=db_instance)

    def upsert_by_external_id(self, data_dict):
        with self.session_scope() as session:
            instance = session.query(self.model).filter_by(auction_id=data_dict.get("auction_id")).first()
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)