import re
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

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
    'regular bottle': 750
}

def parse_unit_format(unit_format: str) -> Optional[Union[str, int]]:
    s = unit_format.strip().lower()

    if s in {"n/a", "na", "none", ""}:
        return None
    
    match = re.match(r'(\d+)\s*[xX*]\s*(full\s*size)', s)
    if match:
        qty, _ = match.groups()
        return int(qty) * 750
    
    match = re.match(r'(\d+)\s*[xX*]\s*(\d+)$', s)
    if match:
        qty, ml = match.groups()
        return int(qty) * int(ml)
    
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
        
    match = re.match(r'(\d+(?:\.\d+)?)\s*([a-z]+)', s)
    if match:
        num, unit = match.groups()
        if unit in VOLUME_IDENTIFIER:
            return int(float(num) * VOLUME_IDENTIFIER[unit])

    if s in VOLUME_IDENTIFIER:
        return int(VOLUME_IDENTIFIER[s])

    if s == "full size":
        return 750
    
    logger.warning(f"Unknown unit format: {unit_format}")

    return None

def extract_unit_and_unit_format(unit_format: str) -> Optional[Union[str, int]]:
    s = unit_format.strip().lower()

    if s in {"n/a", "na", "none", ""}:
        return None, None
    
    match = re.match(r'(\d+)\s*[xX*]\s*(full\s*size)', s)
    if match:
        qty, _ = match.groups()
        return int(qty), '750ml'
    
    match = re.match(r'(\d+)\s*[xX*]\s*(\d+)$', s)
    if match:
        qty, ml = match.groups()
        return int(qty), f'{ml}ml'

    match = re.match(r'(\d+)\s*[xX*]\s*([a-z]+)', s)
    if match:
        qty, unit = match.groups()
        return int(qty), unit

    match = re.match(r'(\d+(?:\.\d+)?)\s*([a-z]+)', s)
    if match:
        num, unit = match.groups()
        return 1, f'{num}{unit}'

    if s == "full size":
        return 1, '750ml'
    
    if s in VOLUME_IDENTIFIER:
        return 1, s

    logger.warning(f"Unknown unit format for extraction: {unit_format}")

    return None, None
