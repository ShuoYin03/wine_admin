from __future__ import annotations
from typing import Callable, TypeVar
from .base_database_client import BaseDatabaseClient
from shared.database.models.auction_db import AuctionModel

T = TypeVar("T")


class AuctionsClient(BaseDatabaseClient):
    def __init__(self, db_instance: object | None = None) -> None:
        super().__init__(AuctionModel, db_instance=db_instance)

    def get_all_by_auction_house(self, auction_house: str, mapper: Callable[[AuctionModel], T]) -> list[T]:
        with self.session_scope() as session:
            results = session.query(AuctionModel).filter_by(auction_house=auction_house).all()
            return [mapper(a) for a in results]

    def query_single_auction(self, auction_id: str, mapper: Callable[[AuctionModel], T]) -> T | None:
        with self.session_scope() as session:
            result = session.query(AuctionModel).filter_by(external_id=auction_id).first()
            return mapper(result) if result else None

    def query_auctions(
        self,
        mapper: Callable[[AuctionModel], T],
        filters: list | None = None,
        order_by: str | list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        return_count: bool = False,
    ) -> tuple[list[T], int | None]:
        with self.session_scope() as session:
            table_map = {"auctions": AuctionModel}
            query = session.query(AuctionModel)
            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            count: int | None = self.get_table_count(session, filters=filters, table_map=table_map) if return_count else None
            data: list[T] = [mapper(a) for a in query.all()]
            return (data, count)
