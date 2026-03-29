def justify_ops(filters: list) -> list:
    justify_keys = [
        "lot_producer",
        "vintage",
        "unit_format",
        "lot_type",
        "wine_type"
    ]

    for f in filters:
        if isinstance(f, dict) and f.get("field") in justify_keys:
            f["op"] = "@>"

    return filters