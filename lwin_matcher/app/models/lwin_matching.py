from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class LwinMatching(BaseModel):
    id: Optional[int] = None
    lot_id: Optional[int] = None
    matched: Optional[str] = None
    lwin: Optional[List[int]] = None
    lwin_11: Optional[List[int]] = None
    match_item: Optional[Dict[str, Any]] = None
    match_score: Optional[List[float]] = None

    class Config:
        from_attributes = True