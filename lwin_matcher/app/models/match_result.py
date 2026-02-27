from enum import Enum

class MatchResult(Enum):
    EXACT_MATCH = "exact_match"
    MULTI_MATCH = "multi_match"
    NOT_MATCH = "not_match"