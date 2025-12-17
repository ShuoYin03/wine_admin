from datetime import date, datetime
import numpy as np

def serialize_for_json(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_for_json(i) for i in obj]
    if isinstance(obj, dict):
        return {
            k: serialize_for_json(v)
            for k, v in obj.items()
        }
    return obj

def justify_ops(filters):
    justify_keys = [
        "lot_producer",
        "vintage",
        "unit_format",
        "lot_type",
        "wine_type"
    ]

    for filter in filters:
        if filter[0] in justify_keys:
            filter[1] = "contains"

    return filters