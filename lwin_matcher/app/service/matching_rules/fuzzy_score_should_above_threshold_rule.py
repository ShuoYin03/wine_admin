
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
from rapidfuzz import fuzz
import re

class FuzzyScoreShouldAboveThresholdRule(Specification):
    def __init__(self):
        super().__init__()

    def _transform_wine_name(self, name: str) -> str:
        remove_terms = ["Château le", "Chateau le", "Château", "Chateau"]
        for term in remove_terms:
            name = name.replace(term, "")

        name = re.sub(r'\s*\(.*?\)\s*$', '', name)
        name = re.sub(r'\b\d{4}\b', '', name)

        return name.lower().strip()
    
    def _standardize_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row
        params: LwinMatchingParams = ctx.params

        fuzzy_filters = [
            (params.lot_producer, row.get('producer_name')),
            (params.country, row.get('country')),
            (params.region, row.get('region')),
            (params.sub_region, row.get('sub_region')),
        ]

        for param_val, row_val in fuzzy_filters:
            if param_val and row_val and isinstance(param_val, str) and isinstance(row_val, str):
                if fuzz.partial_ratio(param_val.lower(), row_val.lower()) < 80:
                    return False

        return True