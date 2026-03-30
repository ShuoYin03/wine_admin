from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date as dateType


class FxRate(BaseModel):
    id: int | None = None
    rates_from: str | None = Field(None, max_length=10)
    rates_to: str | None = Field(None, max_length=10)
    date: dateType | None = None
    rates: float | None = None

    class Config:
        from_attributes = True
