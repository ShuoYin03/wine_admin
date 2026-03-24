def justify_ops(filters):
    justify_keys = [
        "lot_producer",
        "vintage",
        "unit_format",
        "lot_type",
        "wine_type"
    ]

    for f in filters:
        field = f["field"] if isinstance(f, dict) else f[0]
        if field in justify_keys:
            if isinstance(f, dict):
                f["op"] = "@>"
            else:
                f[1] = "@>"

    return filters