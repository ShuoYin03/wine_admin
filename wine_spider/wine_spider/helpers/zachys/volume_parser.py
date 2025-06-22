import re
from wine_spider.exceptions import UnknownWineVolumeFormatException
from wine_spider.helpers.static import VOLUME_IDENTIFIER

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
