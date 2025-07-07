from .base_database_client import BaseDatabaseClient
from .model import LotItemModel, AuctionModel, LotModel

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

    def get_all_by_auction(self, auction_id):
        with self.session_scope() as session:
            query = (session.query(self.model, LotModel, AuctionModel)
                .join(LotModel, LotModel.external_id == self.model.lot_id)
                .join(AuctionModel, AuctionModel.external_id == LotModel.auction_id)
                .filter(AuctionModel.external_id == auction_id)
            )

            results = query.all()

            data = []
            for lot_item, _, _ in results:
                data.append({
                    "id": lot_item.id,
                    "lot_id": lot_item.lot_id,
                    "lot_producer": lot_item.lot_producer,
                    "vintage": lot_item.vintage,
                    "unit_format": lot_item.unit_format,
                    "wine_colour": lot_item.wine_colour,
                })
            
            return data