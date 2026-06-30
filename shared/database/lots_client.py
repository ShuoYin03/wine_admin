from .base_database_client import BaseDatabaseClient
from shared.database.models.lot_db import LotModel
from shared.database.models.lot_item_db import LotItemModel
from shared.database.models.auction_db import AuctionModel
from shared.database.models.lwin_matching_db import LwinMatchingModel
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload, contains_eager

class LotsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LotModel, db_instance=db_instance)
        
    def get_all_by_auction(self, auction_id):
        with self.session_scope() as session:
            lots = session.query(LotModel).filter_by(auction_id=auction_id).all()
            return [lot.model_to_dict() for lot in lots]

    def count_by_auction(self, auction_id):
        with self.session_scope() as session:
            return session.query(func.count(LotModel.id)).filter_by(auction_id=auction_id).scalar()

    def has_lots_for_auction(self, auction_id):
        return (self.count_by_auction(auction_id) or 0) > 0
        
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
        
    def query_lots_with_items_and_auction(self, filters=None, order_by=None, limit=None, offset=None, return_count=False, return_auction=False, auction_house=None):
        with self.session_scope() as session:
            lots = LotModel
            table_map = {"lots": lots, "auctions": AuctionModel, "items": LotItemModel}

            query = session.query(lots)

            if auction_house is not None:
                # Explicit JOIN required for filtering; use contains_eager if we also
                # need to load the relationship (avoids a duplicate join).
                query = query.join(LotModel.auction).filter(
                    AuctionModel.auction_house == auction_house
                )
                if return_auction:
                    query = query.options(
                        contains_eager(lots.auction),
                        selectinload(lots.items),
                    )
                else:
                    query = query.options(selectinload(lots.items))
            else:
                if return_auction:
                    query = query.options(
                        joinedload(lots.auction),
                        selectinload(lots.items),
                    )
                else:
                    query = query.options(selectinload(lots.items))

            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            # count — inline to support auction_house join
            count = None
            if return_count:
                count_query = session.query(func.count(LotModel.id))
                if auction_house is not None:
                    count_query = count_query.join(LotModel.auction).filter(
                        AuctionModel.auction_house == auction_house
                    )
                conditions = self.parse_filters(filters, table_map)
                if conditions is not None:
                    count_query = count_query.filter(conditions)
                count = count_query.scalar()

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

    def query_lot_items_for_lwin_matching(
        self,
        filters=None,
        auction_house=None,
        last_lot_item_id=0,
        limit=None,
        only_missing=False,
        return_count=False,
    ):
        with self.session_scope() as session:
            lots = LotModel
            items = LotItemModel
            auctions = AuctionModel
            lwin_matching = LwinMatchingModel
            table_map = {"lots": lots, "items": items, "auctions": auctions}

            def apply_common_filters(query):
                query = query.select_from(items).join(
                    lots, items.lot_id == lots.external_id
                )
                if auction_house is not None:
                    query = query.join(
                        auctions, lots.auction_id == auctions.external_id
                    ).filter(auctions.auction_house == auction_house)
                if only_missing:
                    query = query.outerjoin(
                        lwin_matching,
                        lwin_matching.lot_item_id == items.id,
                    ).filter(lwin_matching.id.is_(None))
                conditions = self.parse_filters(filters, table_map)
                if conditions is not None:
                    query = query.filter(conditions)
                if last_lot_item_id is not None:
                    query = query.filter(items.id > last_lot_item_id)
                return query

            count = None
            if return_count:
                count_query = apply_common_filters(session.query(func.count(items.id)))
                count = count_query.scalar()

            query = apply_common_filters(session.query(items, lots))
            query = query.order_by(items.id.asc())
            if limit is not None:
                query = query.limit(limit)

            results = query.all()
            data = []
            for item, lot in results:
                data.append({
                    "lot_item_id": item.id,
                    "wine_name": lot.lot_name,
                    "lot_producer": item.lot_producer,
                    "vintage": item.vintage,
                    "region": lot.region,
                    "sub_region": lot.sub_region,
                    "country": lot.country,
                    "colour": item.wine_colour,
                    "lot_external_id": lot.external_id,
                })

            return (data, count) if return_count else (data, None)
