from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date


class Lot(BaseModel):
    id: int | None = None
    external_id: str | None = None
    auction_id: str | None = None
    lot_name: str | None = None
    lot_type: list[str] | None = None
    volume: float | None = None
    unit: int | None = None
    original_currency: str | None = Field(None, max_length=10)
    start_price: int | None = None
    end_price: float | None = None
    low_estimate: int | None = None
    high_estimate: int | None = None
    sold: bool | None = None
    sold_date: date | None = None
    region: str | None = Field(None, max_length=100)
    sub_region: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=50)
    success: bool | None = None
    url: str | None = None

    class Config:
        from_attributes = True