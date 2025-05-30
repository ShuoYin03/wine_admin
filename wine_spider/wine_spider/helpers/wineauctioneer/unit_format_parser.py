import re
from typing import Optional, Union

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

def parse_unit_format(unit_format: str) -> Optional[Union[str, int]]:
    s = unit_format.strip().lower()

    match = re.match(r'(\d+)\s*[xX*]\s*(\w+)', s)
    if match:
        qty, unit = match.groups()
        qty = int(qty)
        if unit in VOLUME_IDENTIFIER:
            return int(qty * VOLUME_IDENTIFIER[unit])
        
        num_unit_match = re.match(r'(\d+(?:\.\d+)?)([a-zA-Z]+)', unit)
        if num_unit_match:
            num, base_unit = num_unit_match.groups()
            if base_unit in VOLUME_IDENTIFIER:
                return int(qty * float(num) * VOLUME_IDENTIFIER[base_unit])

    match = re.match(r'(\d+(?:\.\d+)?)([a-zA-Z]+)', s)
    if match:
        num, unit = match.groups()
        if unit in VOLUME_IDENTIFIER:
            return int(float(num) * VOLUME_IDENTIFIER[unit])

    if s in VOLUME_IDENTIFIER:
        return int(VOLUME_IDENTIFIER[s])

    if s == "full size":
        return 750
    
    return None

def extract_unit_and_unit_format(unit_format: str) -> Optional[Union[str, int]]:
    s = unit_format.strip().lower()

    match = re.match(r'(\d+)\s*[xX*]\s*(\d+(?:\.\d+)?[a-z]+)', s)
    if match:
        qty, unit = match.groups()
        return int(qty), unit

    match = re.match(r'(\d+(?:\.\d+)?[a-z]+)', s)
    if match:
        unit = match.group(1)
        return 1, unit

    if s == "full size":
        return 1, '750ml'

    return None