
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext

class ColourShouldMatchRule(Specification):
    def __init__(self):
        super().__init__()
    
    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row
        params: LwinMatchingParams = ctx.params

        # Temporary fix for float colour values
        if isinstance(params.colour, float):
            return True
        
        if params.colour is None or \
           row.get("colour") is None or \
           ("red" not in params.colour.lower() and \
           "white" not in params.colour.lower()):
            return True

        if "red" in params.colour.lower() and "red" in row.get("colour", "").lower():
            return True
        
        if "white" in params.colour.lower() and "white" in row.get("colour", "").lower():
            return True
        
        return False