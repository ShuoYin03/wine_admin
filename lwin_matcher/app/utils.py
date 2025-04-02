from datetime import date, datetime

def serialize_for_json(obj):
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