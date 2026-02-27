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