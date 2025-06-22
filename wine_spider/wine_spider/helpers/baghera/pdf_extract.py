import re

def extract_lot_part(line: str) -> str:
    match = re.match(r"^(\d+.*?)\s(\d{1,3}(?:’\d{3})?)", line.strip())
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return ""