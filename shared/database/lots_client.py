from .base_database_client import BaseDatabaseClient
from .model import LotModel, AuctionModel, LotItemModel
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

class LotsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotModel, db_instance=db_instance)
        
    def get_all_by_auction(self, auction_id):
        with self.session_scope() as session:
            lots = session.query(LotModel).filter_by(auction_id=auction_id).all()
            return [lot.model_to_dict() for lot in lots]
        
    def sample_lots_with_lot_items(self, sample_size=10, auction_house=None, filters=None, lot_type=None):
        with self.session_scope() as session:
            lots = LotModel
            items = LotItemModel
            auctions = AuctionModel
            table_map = {"lots": lots, "items": items, "auctions": auctions}

            query = session.query(LotModel).\
                join(LotModel.items).\
                join(LotModel.auction).\
                group_by(LotModel.id).\
                having(func.count(LotItemModel.id) > 0)
            query = query.options(joinedload(LotModel.items))
            query = self.apply_filters(query, filters, table_map)
            if auction_house:
                query = query.filter(auctions.auction_house == auction_house)
            if lot_type:
                query = query.filter(lots.lot_type == lot_type)
            query = query.order_by(func.random()).limit(sample_size)
            results = query.all()
            data = [
                {
                    **lot.model_to_dict(),
                    "lot_items": [item.model_to_dict() for item in lot.items]
                }
                for lot in results
            ]
            return data

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
        
    def query_lots_with_items_and_auction(self, filters=None, order_by=None, limit=None, offset=None, return_count=False, return_auction=False):
        with self.session_scope() as session:
            lots = LotModel
            table_map = {"lots": lots, "auctions": AuctionModel, "items": LotItemModel}

            # 基础查询
            query = session.query(lots)

            # 预加载关联
            if return_auction:
                query = query.options(
                    joinedload(lots.auction),      # 一次性加载 auction
                    selectinload(lots.items)       # 批量加载 items（对一对多更高效）
                )
            else:
                query = query.options(selectinload(lots.items))

            # 过滤 + 排序 + 分页
            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            # count
            count = None
            if return_count:
                count = self.get_table_count(session, filters=filters, table_map=table_map)

            # 执行查询
            results = query.all()

            # 转 dict
            data = []
            for lot in results:
                lot_dict = lot.model_to_dict()
                lot_dict["lot_items"] = [item.model_to_dict() for item in lot.items]
                if return_auction:
                    lot_dict["auction"] = lot.auction.model_to_dict() if lot.auction else None
                data.append(lot_dict)

            return (data, count) if return_count else (data, None)