from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext

class NotAssortmentCaseRule(Specification):
    def __init__(self):
        super().__init__()
    
    def _transform_wine_name(self, name: str) -> str:
        if not name:
            return ""
        return name.lower().strip()
    
    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row

        transformed_display_name = self._transform_wine_name(row.get("display_name", ""))
        transformed_wine = self._transform_wine_name(row.get("wine", ""))

        if "assortment" in transformed_display_name or "assortment" in transformed_wine:
            return False
        
        return True