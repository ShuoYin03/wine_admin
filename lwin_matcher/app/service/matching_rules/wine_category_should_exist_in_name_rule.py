
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
from rapidfuzz import fuzz

class WineCategoryShouldExistInNameRule(Specification):
    def __init__(self):
        super().__init__()
    
    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row
        params: LwinMatchingParams = ctx.params

        if not row.get("wine"):
            return True
        
        if fuzz.partial_ratio(params.wine_name.lower(), row.get("wine").lower()) < 80:
            return False

        return True