
from app.service.matching_rules.specification import Specification
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
from app.utils.map_wine_name import map_wine_name
import re

class BurgundyRule(Specification):
    def __init__(self):
        super().__init__()

    def _transform_wine_name(self, name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        remove_terms = ["Château le", "Chateau le", "Château", "Chateau"]
        for term in remove_terms:
            name = name.replace(term, "")

        name = re.sub(r'\s*\(.*?\)\s*$', '', name)
        name = re.sub(r'\b\d{4}\b', '', name)

        return name.lower().strip()
    
    def _standardize_text(self, text: str) -> str:
        if not text or not isinstance(text, str):
            return ""

        text = text.lower()
        text = re.sub(r'[-‐-‒–—―]', ' ', text)
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    
    def is_satisfied_by(self, ctx: MatchingContext):
        row = ctx.row
        params: LwinMatchingParams = ctx.params
        
        if (params.region and "burgundy" not in params.region.lower()) and \
            (params.country and "burgundy" not in params.country.lower()) and \
            (params.sub_region and "burgundy" not in params.sub_region.lower()):
            return True
        
        cleaned_name = self._transform_wine_name(params.wine_name)
        mapped_cleaned_name = map_wine_name(cleaned_name)

        if params.sub_region and row.get("sub_region") and (not (row.get("sub_region").lower() == params.sub_region.lower() or \
            self._standardize_text(row.get("sub_region")) in cleaned_name)):
            return False
        
        if not (self._standardize_text(params.lot_producer) == self._standardize_text(row.get("producer_name") or "") or \
           self._standardize_text(params.lot_producer) == self._standardize_text(((row.get("producer_title") or "") + ' ' + (row.get("producer_name") or "")).strip()) or \
           self._standardize_text(row.get("producer_name") or "") in cleaned_name or \
            self._standardize_text(row.get("producer_title") or "") in mapped_cleaned_name):
            return False

        return True