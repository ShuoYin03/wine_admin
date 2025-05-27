from typing import List
from wine_spider.items import LotDetailItem

def expand_to_lot_items(
    lot_producer: List[str],
    vintage: List[str],
    unit_format: List[str],
    wine_colour: List[str]
) -> List[LotDetailItem]:
    max_length = max(len(lot_producer), len(vintage), len(unit_format), len(wine_colour), 1)

    def pad(field: List, name: str) -> List:
        if len(field) == max_length:
            return field
        elif len(field) == 1:
            return field + [field[0]] * (max_length - 1)
        else:
            return field + [None] * (max_length - len(field))

    lot_producer = pad(lot_producer, "lot_producer")
    vintage = pad(vintage, "vintage")
    unit_format = pad(unit_format, "unit_format")
    wine_colour = pad(wine_colour, "wine_colour")

    result = []
    for i in range(max_length):
        lot_item = LotDetailItem()
        lot_item["lot_producer"] = lot_producer[i]
        lot_item["vintage"] = vintage[i]
        lot_item["unit_format"] = unit_format[i]
        lot_item["wine_colour"] = wine_colour[i]
        result.append(lot_item)

    return result