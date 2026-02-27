
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
import re

class BordeauxRule(Specification):
    def __init__(self):
        super().__init__()

    def _char_difference(self, a: str, b: str) -> int:
        a = a or ""
        b = b or ""

        if a == b:
            return 0

        if not a:
            return len(b)

        if not b:
            return len(a)

        if len(a) > len(b):
            a, b = b, a

        previous_row = list(range(len(a) + 1))
        for i, b_ch in enumerate(b, start=1):
            current_row = [i]
            for j, a_ch in enumerate(a, start=1):
                insert_cost = current_row[j - 1] + 1
                delete_cost = previous_row[j] + 1
                replace_cost = previous_row[j - 1] + (0 if a_ch == b_ch else 1)
                current_row.append(min(insert_cost, delete_cost, replace_cost))
            previous_row = current_row

        return previous_row[-1]
    
    def _transform_wine_name(self, name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        remove_terms = ["château", "chateau", "vintage"]
        for term in remove_terms:
            name = name.replace(term, "")

        name = re.sub(r'\s*\(.*?\)\s*$', '', name)
        name = re.sub(r'\b\d{4}\b', '', name)

        name = re.sub(r"[^\w\s]", " ", name, flags=re.UNICODE)
        name = name.replace("_", " ")
        name = re.sub(r"\s+", " ", name)

        return name.lower().strip()

    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row   
        params: LwinMatchingParams = ctx.params

        if ("bordeaux" not in params.region.lower() if params.region else True) and \
           ("bordeaux" not in params.sub_region.lower() if params.sub_region not in (None, "") else True):
            return True

        standarised_name = self._transform_wine_name(params.wine_name)
        standarised_producer_name = self._transform_wine_name(row.get("producer_name"))

        if standarised_producer_name == standarised_name or \
           standarised_producer_name in standarised_name or \
           self._char_difference(standarised_producer_name, standarised_name) <= 2:
            return True
        
        return False
        
        