from __future__ import annotations

from dataclasses import dataclass
from flask import request
from app.utils.justify_ops import justify_ops


@dataclass
class QueryParams:
    filters: list
    order_by: str | None
    page: int
    page_size: int
    return_count: bool
    offset: int


def parse_query_payload() -> QueryParams:
    payload: dict = request.get_json() or {}
    page = int(payload.get("page", 1))
    page_size = int(payload.get("page_size", 30))
    filters: list = justify_ops(payload.get("filters", []))
    return QueryParams(
        filters=filters,
        order_by=payload.get("order_by"),
        page=page,
        page_size=page_size,
        return_count=bool(payload.get("return_count", False)),
        offset=(page - 1) * page_size,
    )
