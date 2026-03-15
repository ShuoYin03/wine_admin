from __future__ import annotations
from pydantic import BaseModel, Field
from shared.currency.models import CurrencyCode


class AuctionSales(BaseModel):
    id: int | None = None
    auction_id: str | None = None
    lots: int | None = None
    sold: int | None = None
    currency: CurrencyCode | None = None
    total_low_estimate: int | None = None
    total_high_estimate: int | None = None
    total_sales: int | None = None
    volume_sold: float | None = None
    top_lot: str | None = None
    sale_type: str | None = Field(None, max_length=50)
    single_cellar: bool | None = None
    ex_ch: bool | None = None

    class Config:
        from_attributes = True
