from fractions import Fraction
import re
from typing import Optional, Union
import logging
from ..static import VOLUME_IDENTIFIER

logger = logging.getLogger(__name__)

def parse_unit_format(unit_format: str) -> Optional[Union[str, int]]:
    s = unit_format.strip().lower()
    
    # 处理 "数字 x 数字" 格式
    match = re.match(r'(\d+)\s*[xX*]\s*(\d+)$', s)
    if match:
        qty, ml = match.groups()
        return int(qty) * int(ml)
    
    # 处理 "数字 x 单位" 格式
    match = re.match(r'(\d+)\s*[xX*]\s*(\w+)', s)
    if match:
        qty, unit = match.groups()
        qty = int(qty)
        if unit in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[unit] is not None:
            return int(qty * VOLUME_IDENTIFIER[unit])
        
        num_unit_match = re.match(r'(\d+(?:\.\d+)?)([a-zA-Z]+)', unit)
        if num_unit_match:
            num, base_unit = num_unit_match.groups()
            if base_unit in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[base_unit] is not None:
                return int(qty * float(num) * VOLUME_IDENTIFIER[base_unit])

    # 处理分数格式，如 "1/2 gallon", "4/5 qt"
    match = re.match(r'(\d+/\d+)\s+([a-zA-Z]+)', s)
    if match:
        fraction_str, unit = match.groups()
        try:
            fraction_value = float(Fraction(fraction_str))
            if unit in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[unit] is not None:
                return int(fraction_value * VOLUME_IDENTIFIER[unit])
        except:
            pass

    # 处理 "数字+单位" 格式（紧贴）
    match = re.match(r'(\d+(?:\.\d+)?)([a-zA-Z]+)', s)
    if match:
        num, unit = match.groups()
        if unit in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[unit] is not None:
            return int(float(num) * VOLUME_IDENTIFIER[unit])
        
    # 处理 "数字 单位" 格式（有空格）
    match = re.match(r'(\d+(?:\.\d+)?)\s+([a-z]+)', s)
    if match:
        num, unit = match.groups()
        if unit in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[unit] is not None:
            return int(float(num) * VOLUME_IDENTIFIER[unit])

    # 处理只有单位的情况
    if s in VOLUME_IDENTIFIER and VOLUME_IDENTIFIER[s] is not None:
        return int(VOLUME_IDENTIFIER[s])
    
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
