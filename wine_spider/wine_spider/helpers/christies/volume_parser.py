import re
from wine_spider.exceptions import UnknownWineVolumeFormatException
from ..static import VOLUME_IDENTIFIER

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