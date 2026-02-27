from typing import Optional
from pydantic import BaseModel, field_validator

class LwinMatchingParams(BaseModel):
    wine_name: str
    lot_producer: Optional[str] = None
    vintage: Optional[int] = None
    region: Optional[str] = None
    sub_region: Optional[str] = None
    country: Optional[str] = None
    colour: Optional[str] = None

    @field_validator("vintage", mode="before")
    @classmethod
    def clean_vintage(cls, v):
        if v is None:
            return None

        if isinstance(v, str):
            v = v.strip().lower()
            if v in {"nv", "n.v.", "non-vintage", ""}:
                return None

            if v.isdigit():
                return int(v)

            return None
        elif isinstance(v, int):
            return v

        return None

    @field_validator("wine_name", "lot_producer", "country", "region", "sub_region", "colour", mode="before")
    @classmethod
    def ensure_string(cls, v):
        return v if isinstance(v, str) else ""



    


