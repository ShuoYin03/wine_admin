import requests
import json
import os
import sys

API_URL = "http://localhost:5000/lot_query"

def get_unique_filters(filter_type: list[str]):
    for type in filter_type:
        payload = {
            "select_fields": [f"{type}"],
            "distinct_fields": f"{type}",
        }

        response = requests.post(API_URL, json=payload)
        data = response.json()['lots']
        target_data = set()
        for i in range(len(data)):
            if isinstance(data[i], list):
                target_data.add(data[i][0])
            else:
                target_data.add(data[i])
        target_data = list(target_data)
        target_data = [x for x in target_data if x is not None]
        target_data.sort()
        with open(f'{type}.json', 'w') as f:
            json.dump(target_data, f, indent=4)
    
get_unique_filters([
    "lot_producer",
    "region",
    "unit_format"
])