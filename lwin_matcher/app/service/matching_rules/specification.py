from abc import ABC, abstractmethod
from app.service.matching_rules.matching_context import MatchingContext

class Specification(ABC):
    @abstractmethod
    def is_satisfied_by(self, context: MatchingContext) -> bool:
        pass

    def __and__(self, other):
        from .and_specification import AndSpecification
        return AndSpecification(self, other)

    def __or__(self, other):
        from .or_specification import OrSpecification
        return OrSpecification(self, other)

    def __invert__(self):
        from .not_specification import NotSpecification
        return NotSpecification(self)