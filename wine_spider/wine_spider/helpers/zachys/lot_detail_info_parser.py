import re
from typing import List, Tuple, Union

def extract_lot_detail_info(text: str, mode: str = "volume") -> Union[List[Tuple[str, str]], List[str]]:
    if mode == "volume":
        pattern = re.compile(r'\b(\d+)\s+(\d+(?:\.\d+)?(?:ml|l|L))\b', re.IGNORECASE)
        results = pattern.findall(text)
        return [(qty, vol.upper()) for qty, vol in results]
    
    elif mode == "vintage":
        pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        return pattern.findall(text)
    
# print(extract_lot_detail_info(text, mode="vintage"))