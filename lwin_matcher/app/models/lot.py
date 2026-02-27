from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

class Lot(BaseModel):
    id: Optional[int] = None
    external_id: Optional[str] = None
    auction_id: Optional[str] = None
    lot_name: Optional[str] = None
    lot_type: Optional[List[str]] = None
    volume: Optional[float] = None
    unit: Optional[int] = None
    original_currency: Optional[str] = Field(None, max_length=10)
    start_price: Optional[int] = None
    end_price: Optional[float] = None
    low_estimate: Optional[int] = None
    high_estimate: Optional[int] = None
    sold: Optional[bool] = None
    sold_date: Optional[date] = None
    region: Optional[str] = Field(None, max_length=100)
    sub_region: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=50)
    success: Optional[bool] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True