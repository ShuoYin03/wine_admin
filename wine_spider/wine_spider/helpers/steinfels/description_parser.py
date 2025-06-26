from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Any, Tuple, Union
import re
from wine_spider.helpers.static import VOLUME_IDENTIFIER

def extract_quantity_and_unit(line: str) -> Tuple[Optional[float], Optional[str]]:
    line = line.lower().strip()

    if extract_vintages(line):
        return None, None
    
    patterns = [
        r'(\d+)\s*(\d+/\d+)\s*(.*)',
        r'(\d+[.,/]?\d*)\s*(.*)',
    ]
    
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            if len(match.groups()) == 3:
                whole, fraction, unit = match.groups()
                try:
                    qty = float(whole) + eval(fraction)
                except:
                    qty = float(whole)
            else:
                raw_qty, unit = match.groups()
                if '/' in raw_qty:
                    try:
                        qty = float(eval(raw_qty))
                    except:
                        qty = None
                else:
                    try:
                        qty = float(raw_qty.replace(',', '.'))
                    except:
                        qty = None
            
            return qty, unit.strip() if unit else None
    
    return None, None

def extract_vintages(text: str) -> List[int]:
    vintages = set()
    
    range_matches = re.findall(r'\b(19\d{2}|20\d{2})\s*[-–]\s*(19\d{2}|20\d{2})\b', text)
    range_years = set()
    for match in range_matches:
        start_year = int(match[0])
        end_year = int(match[1])
        for year in range(start_year, end_year + 1):
            range_years.add(year)
    
    individual_years = set()
    year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', text)
    for match in year_matches:
        year = int(match)
        if 1900 <= year <= 2025:
            individual_years.add(year)
    
    standalone_years = individual_years - range_years
    
    if standalone_years:
        vintages = standalone_years

    elif range_matches:
        for match in range_matches:
            start_year = int(match[0])
            if 1900 <= start_year <= 2025:
                vintages.add(start_year)
    
    return sorted(vintages)

def extract_sub_items(text: str) -> List[Dict]:
    lines = text.split('\n')
    sub_items = []
    
    for line in lines:
        line = line.strip()
        match = re.match(r'(\d+)x\s+(.*)', line)
        if match:
            qty = int(match.group(1))
            remainder = match.group(2).strip()
            
            vintages = extract_vintages(remainder)
            
            title = remainder
            for vintage in vintages:
                title = re.sub(r'\b' + str(vintage) + r'\b', '', title).strip()
            title = re.sub(r'\s+', ' ', title).strip(', ').strip()
            
            sub_items.append({
                'quantity': qty,
                'vintage': vintages[0] if vintages else None,
                'title': title,
            })
    
    return sub_items

def get_volume_from_unit(unit_format: str) -> Optional[float]:
    if not unit_format:
        return None
        
    unit_format_clean = unit_format.lower().strip()
    
    volume_patterns = [
        (r'(\d+(?:\.\d+)?)\s*cl', lambda x: float(x) * 10),  # cl 转 ml
        (r'(\d+(?:\.\d+)?)\s*ml', lambda x: float(x)),       # ml
        (r'(\d+(?:\.\d+)?)\s*l', lambda x: float(x) * 1000), # l 转 ml
    ]
    
    for pattern, converter in volume_patterns:
        match = re.search(pattern, unit_format_clean)
        if match:
            return converter(match.group(1))
    
    for key in VOLUME_IDENTIFIER:
        if key in unit_format_clean:
            return VOLUME_IDENTIFIER[key]
    
    return None

def parse_mixed_quantity_unit(text: str) -> Tuple[Optional[List], Optional[List]]:
    mixed_pattern = r'(\d+)\s+(\w+)\s*\+\s*(\d+)\s+(\w+)'
    match = re.search(mixed_pattern, text, re.IGNORECASE)
    
    if match:
        qty1, unit1, qty2, unit2 = match.groups()
        
        quantities = [int(qty1), int(qty2)]
        units = [unit1.lower(), unit2.lower()]
        
        return quantities, units
    
    return None, None

def clean_title(title: str) -> str:
    if not title:
        return title
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[,;:]', '', title)
    return title.strip()

def parse_description(description: str) -> Dict[str, Any]:
    soup = BeautifulSoup(description, 'html.parser')
    cleaned = soup.get_text("\n").strip()
    lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
    
    strong_tag = soup.find('strong')
    span_tag = soup.find('span')
    div_tag = soup.find('div')
    title = strong_tag.get_text(strip=True) if strong_tag else None

    vintages = extract_vintages(cleaned)
    sub_items = extract_sub_items(cleaned)
    
    cleaned_for_title = cleaned
    if title:
        cleaned_for_title = cleaned.replace(title, '').strip()
        lines = [line.strip() for line in cleaned_for_title.split('\n') if line.strip()]
    
    if span_tag:
        cleaned_for_title = cleaned_for_title.replace(span_tag.get_text(strip=True), '').strip()
        lines = [line.strip() for line in cleaned_for_title.split('\n') if line.strip()]

    if div_tag:
        cleaned_for_title = cleaned_for_title.replace(div_tag.get_text(strip=True), '').strip()
        lines = [line.strip() for line in cleaned_for_title.split('\n') if line.strip()]

    quantity = None
    unit_format = None
    volume_ml = None
    total_volume_ml = None
    mixed_quantities, mixed_units = parse_mixed_quantity_unit(cleaned)
    if mixed_quantities is not None and mixed_units is not None:
        quantity = mixed_quantities
        unit_format = mixed_units
    else:
        all_lines = [line.strip() for line in cleaned_for_title.split('\n') if line.strip()]
        for line in all_lines:
            qty, unit = extract_quantity_and_unit(line)
            if qty is not None and unit:
                quantity = qty
                unit_format = unit
                break
    
    if isinstance(quantity, list) and isinstance(unit_format, list):
        total_volume_ml = 0
        volume_list = []
        for i in range(len(quantity)):
            unit_volume = get_volume_from_unit(unit_format[i])
            if unit_volume:
                item_volume = quantity[i] * unit_volume
                total_volume_ml += item_volume
                volume_list.append(unit_volume)
            else:
                volume_list.append(None)
        
        volume_ml = volume_list
    else:
        volume_ml = get_volume_from_unit(unit_format)
        if quantity is not None and volume_ml is not None:
            total_volume_ml = quantity * volume_ml
    
    producer = None
    for line in lines:
        if not re.search(r'\d+\s*(flaschen|magnum|liter|quart|cl|ml)', line.lower()):
            clean_line = line
            for vintage in vintages:
                clean_line = re.sub(r'\b' + str(vintage) + r'\b', '', clean_line)
            clean_line = re.sub(r'\s+', ' ', clean_line).strip(', ').strip()
            if clean_line and clean_line != "Schätzpreis:":
                producer = clean_line
                break
    
    return {
        'text': description,
        'producer': clean_title(producer),
        'title': clean_title(title),
        'quantity': quantity,
        'unit_format': unit_format,
        'volume_ml': volume_ml,
        'total_volume_ml': total_volume_ml,
        'vintages': vintages,
        'sub_items': sub_items
    }