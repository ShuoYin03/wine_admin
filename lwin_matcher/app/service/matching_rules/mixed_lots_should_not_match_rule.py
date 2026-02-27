
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
import re

class MixedLotsShouldNotMatchRule(Specification):
    def __init__(self):
        super().__init__()
        self.mixed_lot_identifiers = ["mixed", "assortment", "vertical", "collection", "selection"]
    
    def is_satisfied_by(self, ctx: MatchingContext):
        params: LwinMatchingParams = ctx.params

        if any(identifier in (params.wine_name or "").lower() for identifier in self.mixed_lot_identifiers):
            return False
        
        if len(params.wine_name) > 150:
            bracket_groups = re.findall(r"\([^)]*\)", params.wine_name)
            if len(bracket_groups) >= 2:
                return False
        
        if isinstance(params.lot_producer, float):
            return True

        if any(identifier in (params.lot_producer or "").lower() for identifier in self.mixed_lot_identifiers):
            return False

        return True