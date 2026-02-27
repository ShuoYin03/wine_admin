from pydantic import BaseModel, Field
from typing import Optional


class AuctionSales(BaseModel):
    id: Optional[int] = None
    auction_id: Optional[str] = None
    lots: Optional[int] = None
    sold: Optional[int] = None
    currency: Optional[str] = Field(None, max_length=10)
    total_low_estimate: Optional[int] = None
    total_high_estimate: Optional[int] = None
    total_sales: Optional[int] = None
    volume_sold: Optional[float] = None
    value_sold: Optional[float] = None
    top_lot: Optional[str] = None
    sale_type: Optional[str] = Field(None, max_length=50)
    single_cellar: Optional[bool] = None
    ex_ch: Optional[bool] = None

    class Config:
        from_attributes = True