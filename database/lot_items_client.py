from .base_database_client import BaseDatabaseClient
from .model import LotItemModel

class LotItemsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotItemModel, db_instance=db_instance)
    
    def upsert_by_external_id(self, data_dict):
        with self.session_scope() as session:
            instance = session.query(self.model).filter_by(lot_id=data_dict.get("lot_id")).first()
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)
    
    def delete_by_external_id(self, external_id):
        with self.session_scope() as session:
            session.query(self.model).filter_by(lot_id=external_id).delete()