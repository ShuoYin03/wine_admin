from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

class Auction(BaseModel):
    id: Optional[int] = None
    external_id: Optional[str] = None
    auction_title: Optional[str] = Field(None, max_length=255)
    auction_house: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    continent: Optional[str] = Field(None, max_length=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    year: Optional[int] = None
    quarter: Optional[int] = None
    auction_type: Optional[str] = Field(None, max_length=50)
    url: Optional[str] = None

    class Config:
        from_attributes = True
    