import re

def extract_years_from_json(lot_json: dict) -> list[str]:
    text1 = lot_json.get("title_primary_txt", "")
    text2 = lot_json.get("description_txt", "")
    pattern = r"\b(?:19|20)\d{2}\b"
    
    matches = re.findall(pattern, text1 + " " + text2)
    years = set()
    
    for match in matches:
        if isinstance(match, tuple):
            year = match[0] + match[1:]
        else:
            year = match
        years.add(year)
    
    return sorted(list(years), key=int)