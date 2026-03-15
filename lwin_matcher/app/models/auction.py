from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date
from app.models.auction_sales import AuctionSales
from app.models.lot import Lot


class Auction(BaseModel):
    id: int | None = None
    external_id: str | None = None
    auction_title: str | None = Field(None, max_length=255)
    auction_house: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    continent: str | None = Field(None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    year: int | None = None
    quarter: int | None = None
    auction_type: str | None = Field(None, max_length=50)
    url: str | None = None
    sales: AuctionSales | None = None
    lots: list[Lot] | None = None

    class Config:
        from_attributes = True
