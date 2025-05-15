from .base_database_client import BaseDatabaseClient
from .model import LwinMatchingModel, LotModel
from sqlalchemy import func

class LwinMatchingClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LwinMatchingModel, db_instance=db_instance)

    def query_lwin_with_lots(self, filters=None, order_by=None, limit=None, offset=None, return_count=False):
        with self.session_scope() as session:
            lwin_matching = LwinMatchingModel
            lots = LotModel
            table_map = {"lwin_matching": lwin_matching, "lots": lots}

            query = session.query(lwin_matching)
            query = query.select_from(lwin_matching).join(lots.lwin).add_entity(lots)

            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            count = None
            if return_count:
                count = self.get_table_count(session)

            results = query.all()
            data = [
                {
                    **lot.model_to_dict(),
                    **auction.model_to_dict(),
                }
                for lot, auction in results
            ]
            
            return (data, count) if return_count else (data, None)
        
    def query_exact_match_count(self):
        with self.session_scope() as session:
            query = session.query(func.count(self.model.id)).filter(self.model.matched == "exact_match")
            count = query.scalar()
            return count
    
    def query_multi_match_count(self):
        with self.session_scope() as session:
            query = session.query(func.count(self.model.id)).filter(self.model.matched == "multi_match")
            count = query.scalar()
            return count
    
    def query_not_match_count(self):
        with self.session_scope() as session:
            query = session.query(func.count(self.model.id)).filter(self.model.matched == "not_match")
            count = query.scalar()
            return count
        
    def upsert_by_external_id(self, data_dict):
        with self.session_scope() as session:
            instance = session.query(self.model).filter_by(lot_id=data_dict.get("lot_id")).first()
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)