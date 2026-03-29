from __future__ import annotations

import math
from typing import Any


def clean_nan(obj: Any) -> Any:
    """Recursively replace NaN/Inf Python floats with None.

    The matching engine guarantees all numpy types are converted before
    returning, so this function only needs to handle pathological float
    values (inf/nan) that can theoretically arise from score arithmetic.
    """
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
