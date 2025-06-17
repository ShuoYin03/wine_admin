VALID_FILTERS = {
    "critere-region": "region",
    "critere-producteur": "lot_producer",
    "critere-nature": "lot_type",
    "critere-type": "wine_colour",
    "region": "region",
    "producteur": "lot_producer",
    "nature": "lot_type",
    "type": "wine_colour",
}

def filter_to_params(filter):
    return VALID_FILTERS.get(filter, None)