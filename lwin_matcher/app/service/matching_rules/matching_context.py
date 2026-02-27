from dataclasses import dataclass
from app.models.lwin_matching_params import LwinMatchingParams

@dataclass
class MatchingContext:
    row: dict
    params: LwinMatchingParams