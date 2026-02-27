from app.service.matching_rules.specification import Specification
from app.service.matching_rules.matching_context import MatchingContext

class OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right

    def is_satisfied_by(self, ctx: MatchingContext):
        return (
            self.left.is_satisfied_by(ctx)
            or self.right.is_satisfied_by(ctx)
        )