import json
import os

if (os.getcwd() == "E:\\Upwork\\WineAdmin\\lwin_matcher"):
    with open("app/utils/mapping_table.json", "r", encoding="utf-8") as f:
        mapping_table_json = json.load(f)
else:
    with open("lwin_matcher/app/utils/mapping_table.json", "r", encoding="utf-8") as f:
        mapping_table_json = json.load(f)

def map_wine_name(name):
    for _, mappings in mapping_table_json.items():
        for key, value in mappings.items():
            name = name.replace(key, value)
    return name