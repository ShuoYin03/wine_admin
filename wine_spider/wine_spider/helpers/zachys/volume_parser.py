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
    'qt': 1136.5,
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

def parse_volume(volume_str: str) -> float:
    volume_str = volume_str.strip().lower()

    if volume_str in VOLUME_IDENTIFIER:
        return VOLUME_IDENTIFIER[volume_str]

    match_number_unit = re.match(r"^(\d+(?:\.\d+)?)\s*(ml|l|cl|qt|pint|gallon|litres?|litrs?|ounces)$", volume_str)
    if match_number_unit:
        value, unit = match_number_unit.groups()
        unit = unit.rstrip("s")  # normalize plural
        multiplier = VOLUME_IDENTIFIER.get(unit)
        if multiplier:
            return float(value) * multiplier

    match_fraction_unit = re.match(r"^(\d+)/(\d+)\s*(qt|pint|gallon)$", volume_str)
    if match_fraction_unit:
        numerator, denominator, unit = match_fraction_unit.groups()
        multiplier = VOLUME_IDENTIFIER.get(unit)
        if multiplier:
            return (int(numerator) / int(denominator)) * multiplier

    raise UnknownWineVolumeFormatException(volume_str)

def combine_volume(volume_list):
    total_volume = 0.0
    for volume_pair in volume_list:
        qty, unit_size = volume_pair
        try:
            volume = parse_volume(unit_size)
            total_volume += float(qty) * volume
        except UnknownWineVolumeFormatException as e:
            continue
    
    return total_volume if total_volume > 0 else None
