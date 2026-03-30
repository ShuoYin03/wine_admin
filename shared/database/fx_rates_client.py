from __future__ import annotations
from datetime import date as DateType
from typing import Callable, TypeVar
from .base_database_client import BaseDatabaseClient
from shared.database.models.fx_rate_db import FxRatesModel

T = TypeVar("T")


class FxRatesClient(BaseDatabaseClient):
    def __init__(self, db_instance: object | None = None) -> None:
        super().__init__(FxRatesModel, db_instance=db_instance)

    def get_single_rate(
        self,
        mapper: Callable[[FxRatesModel], T],
        rates_from: str,
        rates_to: str,
        date: DateType,
    ) -> T | None:
        with self.session_scope() as session:
            result = session.query(self.model).filter_by(
                rates_from=rates_from,
                rates_to=rates_to,
                date=date,
            ).first()
            return mapper(result) if result else None

    def get_rates(
        self,
        mapper: Callable[[FxRatesModel], T],
        filters: list | None = None,
        order_by: str | list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        return_count: bool = False,
    ) -> tuple[list[T], int | None]:
        with self.session_scope() as session:
            table_map = {"fx_rates": FxRatesModel}
            query = session.query(FxRatesModel)
            query = self.apply_filters(query, filters, table_map)
            query = self.apply_sort(query, order_by, table_map)
            query = self.apply_pagination(query, limit, offset)

            count: int | None = (
                self.get_table_count(session, filters=filters, table_map=table_map)
                if return_count
                else None
            )
            data: list[T] = [mapper(r) for r in query.all()]
            return (data, count)
