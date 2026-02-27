
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext

class MissProducerShouldNotMatchRule(Specification):
    def __init__(self):
        super().__init__()
    
    def is_satisfied_by(self, ctx: MatchingContext):
        params: LwinMatchingParams = ctx.params

        if isinstance(params.lot_producer, float):
            return False

        if not params.lot_producer or params.lot_producer.strip() == "":
            return False
        
        return True