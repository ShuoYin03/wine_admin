from pydantic import BaseModel, Field
from typing import Optional

class LotItem(BaseModel):
    id: Optional[int] = None
    lot_id: Optional[str] = None
    lot_producer: Optional[str] = Field(None, max_length=100)
    vintage: Optional[str] = Field(None, max_length=20)
    unit_format: Optional[str] = Field(None, max_length=100)
    wine_colour: Optional[str] = Field(None, max_length=50)

    class Config:
        from_attributes = True
