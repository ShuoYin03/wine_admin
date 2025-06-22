import re
import logging
from typing import List, Tuple
from wine_spider.helpers.static import VOLUME_IDENTIFIER

logger = logging.getLogger(__name__)

def parse_all_valid_quantity_volume(text: str) -> List[Tuple[int, str]]:
    bracket_contents = re.findall(r'\(([^()]*)\)', text)
    results = []

    for content in bracket_contents:
        content = content.strip().lower()
        parts = [p.strip() for p in content.split(",") if p.strip()]

        if len(parts) == 2:
            quantity_part, volume_part = parts
            
            quantity_match = re.search(r'(\d+)', quantity_part)
            if not quantity_match:
                continue
            quantity = int(quantity_match.group(1))
            
            volume_part_clean = volume_part.strip().lower().replace(",", ".")
            
            volume_match = re.match(r'^((?:\d+(?:\.\d+)?|\d+/\d+))\s+([a-z]+(?:\s+[a-z]+)*)$', volume_part_clean)
            if volume_match:
                number, unit = volume_match.groups()
                unit = unit.strip()
                if unit in VOLUME_IDENTIFIER:
                    results.append((quantity, f"{number} {unit}"))
                continue
            
            volume_match = re.match(r'^((?:\d+(?:\.\d+)?|\d+/\d+))([a-z]+)$', volume_part_clean)
            if volume_match:
                number, unit = volume_match.groups()
                if unit in VOLUME_IDENTIFIER:
                    results.append((quantity, f"{number} {unit}"))
            
        else:
            match = re.match(r'^(\d+)\s+\w+\s+(.+)$', content)
            if match:
                quantity_part, volume_part = match.groups()
                
                quantity = int(quantity_part.strip())
                
                volume_part_clean = volume_part.strip().lower().replace(",", ".")
                
                volume_match = re.match(r'^((?:\d+(?:\.\d+)?|\d+/\d+))\s*([a-z]+)$', volume_part_clean)
                if volume_match:
                    number, unit = volume_match.groups()
                    if unit in VOLUME_IDENTIFIER:
                        results.append((quantity, f"{number} {unit}"))

    return results

def extract_all_volume_units(text):
    if not text:
        return []

    text = text.strip().lower()
    results = []

    bracket_contents = re.findall(r'\(([^()]+)\)', text)

    keywords = sorted(VOLUME_IDENTIFIER.keys(), key=lambda k: -len(k))
    unit_pattern = '|'.join(re.escape(k) for k in keywords)

    for bracket in bracket_contents:
        content = bracket.replace(" ,", ",").replace(", ", ",").replace(" , ", ",")

        match_mul = re.search(
            rf'\b(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*({unit_pattern})\b',
            content, flags=re.IGNORECASE
        )
        if match_mul:
            quantity = int(match_mul.group(1))
            number_part = match_mul.group(2).replace(",", ".")
            unit = match_mul.group(3).strip()
            results.append((quantity, f"{number_part} {unit}"))
            continue

        # 匹配 3 x magnums
        match_quantity_unit = re.search(
            rf'\b(\d+)\s*[x×]\s*({unit_pattern})\b',
            content, flags=re.IGNORECASE
        )
        if match_quantity_unit:
            quantity = int(match_quantity_unit.group(1))
            unit_format = match_quantity_unit.group(2).strip()
            results.append((quantity, unit_format))
            continue

        # 匹配 6 bottles
        match_counted_unit = re.search(
            rf'\b(\d+)\s+({unit_pattern})\b',
            content, flags=re.IGNORECASE
        )
        if match_counted_unit:
            quantity = int(match_counted_unit.group(1))
            unit_format = match_counted_unit.group(2).strip()
            results.append((quantity, unit_format))
            continue

        match_unit_only = re.search(
            rf'\b({unit_pattern})\b',
            content, flags=re.IGNORECASE
        )
        if match_unit_only:
            unit_format = match_unit_only.group(1).strip()
            results.append((None, unit_format))
            continue

        logger.warning(f"Unknown volume format in bracket: {text}")

    return results
