import re

def extract_years(text: str) -> list[int]:
    return [int(year) for year in re.findall(r"\b(1[5-9]\d{2}|20\d{2}|2100)\b", text)]