VALID_FILTERS = {
    "critere-region": "region",
    "critere-producteur": "lot_producer",
    "critere-nature": "lot_type",
    "critere-type": "wine_colour"
}

def filter_to_params(filter):
    if filter in VALID_FILTERS:
        return VALID_FILTERS.get(filter, None)