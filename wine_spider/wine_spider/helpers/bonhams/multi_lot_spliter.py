import re
from wine_spider.helpers.static import VOLUME_IDENTIFIER

def is_valid_volume_bracket(content: str) -> bool:
    content = content.lower().replace(" ,", ",").replace(", ", ",").replace(" , ", ",").strip()
    if not content:
        return False

    keywords = sorted(VOLUME_IDENTIFIER.keys(), key=lambda k: -len(k))
    unit_pattern = '|'.join(re.escape(k) for k in keywords)

    # 匹配类型 1 x 750ml
    if re.search(rf'\b\d+\s*[x×]\s*\d+(?:[.,]\d+)?\s*({unit_pattern})\b', content, flags=re.IGNORECASE):
        return True

    # 匹配类型 1 x magnum
    if re.search(rf'\b\d+\s*[x×]\s*({unit_pattern})\b', content, flags=re.IGNORECASE):
        return True

    # 匹配类型 6 bottles
    if re.search(rf'\b\d+\s+({unit_pattern})\b', content, flags=re.IGNORECASE):
        return True

    return False

def split_title_by_valid_brackets(text: str):
    result = []
    last_index = 0

    for match in re.finditer(r'\(([^()]+)\)', text):
        start, end = match.span()
        content = match.group(1)

        if is_valid_volume_bracket(content):
            prefix = text[last_index:start].strip()
            bracket_text = text[start:end].strip()
            result.append((prefix, bracket_text))
            last_index = end

    return result