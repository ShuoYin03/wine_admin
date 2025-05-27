from collections import defaultdict

def make_serializable(obj):
    if isinstance(obj, defaultdict):
        obj = dict(obj)
    if isinstance(obj, dict):
        return {str(k): make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(i) for i in obj]
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif hasattr(obj, "__dict__"):
        return make_serializable(vars(obj))
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        return str(obj)