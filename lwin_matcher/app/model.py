from enum import Enum

class LwinMatchingParams:
    def __init__(self, wine_name, lot_producer, vintage, region, sub_region, country, colour):
        self.wine_name = wine_name
        self.lot_producer = lot_producer
        self.vintage = vintage
        self.country = country
        self.region = region
        self.sub_region = sub_region
        self.colour = colour
    
    def __repr__(self):
        return f"<LwinMatchingParams {self.wine_name} {self.lot_producer} {self.vintage} {self.country} {self.region} {self.sub_region} {self.colour}>"

class MatchResult(Enum):
    EXACT_MATCH = "exact_match"
    MULTI_MATCH = "multi_match"
    NOT_MATCH = "not_match"

