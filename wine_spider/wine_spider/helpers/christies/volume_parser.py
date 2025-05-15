import re
from wine_spider.exceptions import UnknownWineVolumeFormatException

VOLUME_IDENTIFIER = {
    'bt': 750,
    'bts': 750,
    'hb': 375,
    'hfbt': 375,
    'hbs': 375,
    'mag': 1500,
    'mags': 1500,
    'double-magnum': 3000,
    'dm': 3000,
    'l': 1000,
    'cl': 10,
    'pint': 568.3,
    'half-pint': 284.2,
    'quart': 1136.5,
    'gallon': 4546.1,
    'half-gallon': 2273.1,
    'hflt': 500,
    'litr': 1000,
    'litrs': 1000,
    'litre': 1000,
    'litres': 1000,
    'ml': 1,
    'bottle': 750,
    'ounces': 28.4,
    'pce': 228000,
    'imp': 6000,
    'jm30': 3000,
    'jm50': 5000,
    'jm70': 7000,
    'meth': 6000,
    'feu': 114000,
    'salr': 9000,
    'nebr': 15000,
    'balr': 12000,
    'prime': 27000,
}

def parse_qty_and_unit_from_secondary_title(title: str):
    title = title.strip().lower()
    default_unit = 'bottle'

    qty_match = re.search(r"\b(\d+)\b", title)
    if not qty_match:
        raise UnknownWineVolumeFormatException(title)
    qty = int(qty_match.group(1))

    candidates = []

    m = re.search(r'\((.*?)\)', title)
    if m:
        candidates.append(m.group(1).strip())

    m2 = re.search(r'(\d+(?:\.\d+)?)(cl|ml|l|oz)', title)
    if m2:
        candidates.append(m2.group(0).strip())

    for unit_key in VOLUME_IDENTIFIER:
        if unit_key in title:
            candidates.append(unit_key)

    for c in candidates:
        c = c.replace(" ", "").replace("-", "").lower()

        m = re.match(r'(\d+(?:\.\d+)?)([a-z]+)', c)
        if m:
            num = float(m.group(1))
            unit = m.group(2)
            if unit in VOLUME_IDENTIFIER:
                single_volume = num * VOLUME_IDENTIFIER[unit]
                volume = qty * single_volume
                return volume, qty

        if c in VOLUME_IDENTIFIER:
            volume = qty * VOLUME_IDENTIFIER[c]
            return volume, qty

    volume = qty * VOLUME_IDENTIFIER[default_unit]
    return volume, qty

# print(parse_qty_and_unit_from_secondary_title("3 Double-Magnums (300cl) per lot"))