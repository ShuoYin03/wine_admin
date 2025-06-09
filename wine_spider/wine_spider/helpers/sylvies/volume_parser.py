import re
from wine_spider.helpers.static import VOLUME_IDENTIFIER

def extract_volume_unit(text):
    if not text:
        return None, None

    # 统一清理格式
    text = text.strip().lower().replace(" ,", ",").replace(", ", ",").replace(" , ", ",")
    
    # 提前排除无意义信息
    if text in {"0", "0,owc", "0,owc-", "n/a", "none"}:
        return None, None

    keywords = sorted(VOLUME_IDENTIFIER.keys(), key=lambda k: -len(k))
    unit_pattern = '|'.join(re.escape(k) for k in keywords)

    # e.g. "1 x 3,00 Ltr"
    match_mul = re.search(
        rf'\b(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*({unit_pattern})\b',
        text, flags=re.IGNORECASE
    )
    if match_mul:
        quantity = int(match_mul.group(1))
        number_part = match_mul.group(2).replace(",", ".")
        unit = match_mul.group(3).strip()
        return quantity, f"{number_part} {unit}"

    match_counted_unit = re.search(
        rf'\b(\d+)\s+({unit_pattern})\b',
        text, flags=re.IGNORECASE
    )
    if match_counted_unit:
        quantity = int(match_counted_unit.group(1))
        unit_format = match_counted_unit.group(2).strip()
        return quantity, unit_format

    match_owc = re.search(r'\b(?:owc|oc)[\s\-–—]*(\d+)', text, flags=re.IGNORECASE)
    if match_owc:
        quantity = int(match_owc.group(1))
        return quantity, "750ml"

    match_unit_only = re.search(
        rf'\b({unit_pattern})\b',
        text, flags=re.IGNORECASE
    )
    if match_unit_only:
        unit_format = match_unit_only.group(1).strip()
        return None, unit_format

    print(f"Warning: No volume unit found in text: {text}")
    return None, None


def convert_to_volume(unit_format):
    if not unit_format:
        return None

    unit_format = unit_format.strip().lower().replace(",", ".")

    # 新增：处理如 "750ml"、"1500l" 紧凑格式
    compact_match = re.match(r'^(\d+(?:\.\d+)?)([a-zA-Z\-]+)$', unit_format)
    if compact_match:
        number = float(compact_match.group(1))
        unit = compact_match.group(2)
        if unit in VOLUME_IDENTIFIER:
            return number * VOLUME_IDENTIFIER[unit]
        return None

    # 原有匹配：有空格的形式，如 "1.5 L"
    match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z\- ]+)', unit_format, flags=re.IGNORECASE)
    if match:
        number = float(match.group(1))
        unit = match.group(2).strip().lower()
        if unit in VOLUME_IDENTIFIER:
            return number * VOLUME_IDENTIFIER[unit]
        return None

    unit_key = unit_format.strip().lower()
    return VOLUME_IDENTIFIER.get(unit_key, None)
