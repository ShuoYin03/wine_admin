import re
import logging
from wine_spider.helpers.static import VOLUME_IDENTIFIER
from wine_spider.exceptions import NoPreDefinedVolumeIdentifierException, UnknownWineVolumeFormatException

logger = logging.getLogger(__name__)


def unit_format_to_volume(unit_format):
    """Strict dict lookup. Raises NoPreDefinedVolumeIdentifierException if not found."""
    volume = VOLUME_IDENTIFIER.get(unit_format)
    if not volume:
        raise NoPreDefinedVolumeIdentifierException(unit_format)
    return volume


def convert_to_volume(unit_format):
    """
    Convert a unit-format string (e.g. "750ml", "1.5 L", "magnum") to millilitres.
    Returns None when the format is unrecognised.
    """
    if not unit_format:
        return None

    unit_format = unit_format.strip().lower().replace(",", ".")

    # compact form: "750ml", "1500l"
    compact_match = re.match(r'^(\d+(?:\.\d+)?)([a-zA-Z\-]+)$', unit_format)
    if compact_match:
        number = float(compact_match.group(1))
        unit = compact_match.group(2)
        if unit in VOLUME_IDENTIFIER:
            return number * VOLUME_IDENTIFIER[unit]
        return None

    # spaced form: "1.5 L", "75 cl"
    match = re.match(r'(\d+(?:\.\d+)?)\s*([a-zA-Z\- ]+)', unit_format, flags=re.IGNORECASE)
    if match:
        number = float(match.group(1))
        unit = match.group(2).strip().lower()
        if unit in VOLUME_IDENTIFIER:
            return number * VOLUME_IDENTIFIER[unit]
        return None

    return VOLUME_IDENTIFIER.get(unit_format.strip().lower())


def parse_volume(volume_str: str) -> float:
    """
    Parse a volume string (e.g. "750ml", "magnum", "1/2 pint") to millilitres.
    Raises UnknownWineVolumeFormatException when unrecognised.
    """
    volume_str = volume_str.strip().lower()

    if volume_str in VOLUME_IDENTIFIER:
        return VOLUME_IDENTIFIER[volume_str]

    match_number_unit = re.match(
        r"^(\d+(?:\.\d+)?)\s*(ml|l|cl|qt|pint|gallon|litres?|litrs?|ounces)$",
        volume_str,
    )
    if match_number_unit:
        value, unit = match_number_unit.groups()
        unit = unit.rstrip("s")  # normalise plural
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


def combine_volume(volume_list) -> float | None:
    """Sum a list of (qty, unit_format) pairs into a total volume in millilitres."""
    total = 0.0
    for qty, unit_size in volume_list:
        try:
            total += float(qty) * parse_volume(unit_size)
        except UnknownWineVolumeFormatException:
            continue
    return total if total > 0 else None


def extract_volume_unit(text):
    """
    Extract (quantity, unit_format) from an inline text string.
    Returns (None, None) when nothing is recognised.
    """
    if not text:
        return None, None

    text = text.strip().lower().replace(" ,", ",").replace(", ", ",").replace(" , ", ",")

    if text in {"0", "0,owc", "0,owc-", "n/a", "none"}:
        return None, None

    keywords = sorted(VOLUME_IDENTIFIER.keys(), key=lambda k: -len(k))
    unit_pattern = '|'.join(re.escape(k) for k in keywords)

    # "1 x 3,00 Ltr"
    match = re.search(
        rf'\b(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*({unit_pattern})\b',
        text, flags=re.IGNORECASE,
    )
    if match:
        quantity = int(match.group(1))
        number_part = match.group(2).replace(",", ".")
        unit = match.group(3).strip()
        return quantity, f"{number_part} {unit}"

    # "3 x magnums"
    match = re.search(
        rf'\b(\d+)\s*[x×]\s*({unit_pattern})\b',
        text, flags=re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), match.group(2).strip()

    # "6 bottles"
    match = re.search(
        rf'\b(\d+)\s+({unit_pattern})\b',
        text, flags=re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), match.group(2).strip()

    # OWC notation: "owc-6"
    match = re.search(r'\b(?:owc|oc)[\s\-–—]*(\d+)', text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1)), "750ml"

    # bare unit
    match = re.search(rf'\b({unit_pattern})\b', text, flags=re.IGNORECASE)
    if match:
        return None, match.group(1).strip()

    logger.warning("No volume unit found in text: %s", text)
    return None, None
