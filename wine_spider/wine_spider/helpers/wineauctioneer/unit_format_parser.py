import re
from typing import Optional, Union
import logging
from ..static import VOLUME_IDENTIFIER

logger = logging.getLogger(__name__)

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
