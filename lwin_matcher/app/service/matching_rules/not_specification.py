from app.service.matching_rules.specification import Specification
from app.service.matching_rules.matching_context import MatchingContext

class NotSpecification(Specification):
    def __init__(self, spec: Specification):
        self.spec = spec

    def is_satisfied_by(self, ctx: MatchingContext):
        return not self.spec.is_satisfied_by(ctx)