from __future__ import annotations
import datetime
import requests
from flask import current_app
from app.exception.rates_not_found_exception import RatesNotFoundException
from app.mappers.fx_rate_mapper import map_fx_rate
from app.models.fx_rate import FxRate


class FxRatesService:
    def __init__(self) -> None:
        pass

    def get_rate(
        self,
        rates_from: str,
        rates_to: str,
        date: datetime.date,
    ) -> FxRate | None:
        return current_app.fx_rates_client.get_single_rate(
            mapper=map_fx_rate,
            rates_from=rates_from,
            rates_to=rates_to,
            date=date,
        )

    def get_rates(
        self,
        filters: list | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        return_count: bool = False,
    ) -> tuple[list[FxRate], int | None]:
        return current_app.fx_rates_client.get_rates(
            mapper=map_fx_rate,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
            return_count=return_count,
        )