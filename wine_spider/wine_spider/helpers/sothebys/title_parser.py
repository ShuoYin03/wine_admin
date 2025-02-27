import re
import pandas as pd
from collections import Counter
from wine_spider.exceptions import AmbiguousRegionAndCountryMatchException, NoMatchedRegionAndCountryException

VOLUMN_IDENTIFIER = {
    'bt': 75,
    'bts': 75,
    'hb': 75,
    'hbs': 75,
    'mag': 150,
    'mags': 150,
    'l': 1000,
    'cl': 10,
    'pint': 568.3,
    'half-pint': 284.2,
    'quart': 1136.5,
    'gallon': 4546.1,
    'litre': 1000,
    'ml': 1,
    'bottle': 750,
    'ounces': 28.4,
    'mag': 1500,
    'bt': 750,
}

def parse_volumn_and_unit_from_title(title):
    volumn = 0.0
    potential_volumn_strings = re.findall(r'\((.*?)\)', title)
    if not potential_volumn_strings:
        if 'MIXED LOT' in title:
            title = title.replace('MIXED LOT ', '').split(' and ')
            for t in title:
                count, identifier = t.split(' ')[0], t.split(' ')[1]
                volumn += int(count) * VOLUMN_IDENTIFIER[identifier.lower()]
            return volumn, int(count)
        raise ValueError(f"Could not find volumns in title: {title}")
    
    for volumn_string in potential_volumn_strings:
        tokens = re.split(r',\s*', volumn_string)
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            m = re.match(r'^(\d+)\s*(.*)$', token)
            if m:
                qty = float(m.group(1))
                desc = m.group(2).strip()
            else:
                qty = 1
                desc = token
            desc_lower = desc.lower()
            vol = 0.0
            matched = False
            
            # --- BT patterns ---
            # e.g., "BT70" or "bt05"
            if not matched and re.fullmatch(r'bt\d+', desc_lower):
                m_bt = re.fullmatch(r'bt(\d+)', desc_lower)
                if m_bt:
                    vol = float(m_bt.group(1)) * 10
                    matched = True
            # e.g., "BT75cl"
            if not matched and re.fullmatch(r'bt\d+cl', desc_lower):
                m_btcl = re.fullmatch(r'bt(\d+)cl', desc_lower)
                if m_btcl:
                    vol = float(m_btcl.group(1)) * 10
                    matched = True
            # e.g., just "BT"
            if not matched and desc_lower == 'bt':
                vol = VOLUMN_IDENTIFIER['bt']
                matched = True

            # --- Bottle with leading B and digits (e.g., "B757") ---
            if not matched and re.fullmatch(r'b\d+', desc_lower):
                m_b = re.fullmatch(r'b(\d+)', desc_lower)
                if m_b:
                    vol = float(m_b.group(1))
                    matched = True
            
            # --- Fixed keywords: HFLT, MAG, Hogshead ---
            if not matched and desc_lower == 'hflt':
                vol = VOLUMN_IDENTIFIER['hflt']
                matched = True
            if not matched and desc_lower == 'mag':
                vol = VOLUMN_IDENTIFIER['mag']
                matched = True
            if not matched and desc_lower == 'hogshead':
                vol = VOLUMN_IDENTIFIER['hogshead']
                matched = True

            # --- Bottle patterns ---
            # "Bottles 75cl" or "Bottle 75cl"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+\d+cl', desc_lower):
                m_bottle_cl = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+)cl', desc_lower)
                if m_bottle_cl:
                    vol = float(m_bottle_cl.group(1)) * 10
                    matched = True
            # "Bottle 4/5 Quart"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(\d+/\d+)\s+quart', desc_lower):
                m_bottle_quart = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+/\d+)\s+quart', desc_lower)
                if m_bottle_quart:
                    frac_str = m_bottle_quart.group(1)
                    num, den = frac_str.split('/')
                    frac = float(num) / float(den)
                    vol = frac * VOLUMN_IDENTIFIER['quart']
                    matched = True
            # "Bottle 1/5 Gallon"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(\d+/\d+)\s+gallon', desc_lower):
                m_bottle_gallon = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+/\d+)\s+gallon', desc_lower)
                if m_bottle_gallon:
                    frac_str = m_bottle_gallon.group(1)
                    num, den = frac_str.split('/')
                    frac = float(num) / float(den)
                    vol = frac * VOLUMN_IDENTIFIER['gallon']
                    matched = True
            # "Bottle 25 Fluid Oz" (optionally "fluid" may be omitted)
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)\s*(?:fluid\s*)?(?:oz|ounces|oz\.)', desc_lower):
                m_bottle_oz = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)\s*(?:fluid\s*)?(?:oz|ounces|oz\.)', desc_lower)
                if m_bottle_oz:
                    num = float(m_bottle_oz.group(1))
                    vol = num * VOLUMN_IDENTIFIER['ounces']
                    matched = True
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(?:litre|l)$', desc_lower):
                vol = VOLUMN_IDENTIFIER['litre']
                matched = True
            # "Bottle 1.75 Litre" (or "l")
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)\s*(?:litre|l)', desc_lower):
                m_bottle_litre = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)\s*(?:litre|l)', desc_lower)
                if m_bottle_litre:
                    num = float(m_bottle_litre.group(1))
                    vol = num * VOLUMN_IDENTIFIER['litre']
                    matched = True
            # "Bottle Quart"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+quart', desc_lower):
                vol = VOLUMN_IDENTIFIER['quart']
                matched = True
            # "Bottle Half-Pint"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+half[\s-]?pint', desc_lower):
                vol = VOLUMN_IDENTIFIER['half-pint']
                matched = True
            # If descriptor is exactly "bottle" or "bottles" (default)
            if not matched and desc_lower in ['bottle', 'bottles']:
                vol = VOLUMN_IDENTIFIER['bottle']
                matched = True

            # --- UK measures outside of "bottle" context ---
            # "Pint" or "Pints"
            if not matched and desc_lower in ['pint', 'pints']:
                vol = VOLUMN_IDENTIFIER['pint']
                matched = True
            # "Pint 8 Ounces" (allow fractions too)
            if not matched:
                m_pint_oz = re.fullmatch(r'pints?\s+(\d+(?:/\d+)?)\s*(?:ounces|oz\.?)', desc_lower)
                if m_pint_oz:
                    frac_str = m_pint_oz.group(1)
                    if '/' in frac_str:
                        num, den = frac_str.split('/')
                        frac = float(num) / float(den)
                    else:
                        frac = float(frac_str)
                    vol = VOLUMN_IDENTIFIER['pint'] + frac * VOLUMN_IDENTIFIER['ounces']
                    matched = True
            # "Gallon(s)"
            if not matched and desc_lower in ['gallon', 'gallons']:
                vol = VOLUMN_IDENTIFIER['gallon']
                matched = True
            # "Litre" variants
            if not matched and desc_lower in ['litre', 'litres', 'l']:
                vol = VOLUMN_IDENTIFIER['litre']
                matched = True
            
            # Fallback: if descriptor exactly matches a key in VOLUMN_IDENTIFIER:
            if not matched and desc_lower in VOLUMN_IDENTIFIER:
                vol = VOLUMN_IDENTIFIER[desc_lower]
                matched = True
            
            volumn += qty * vol
    

    return volumn, qty

def parse_year_from_title(title):
    m = re.search(r'(\d{4})-(\d{4})', title)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{4})\b', title)
    if m:
        return int(m.group(1))
    return None

# def parse_possible_producer_from_title(title):
#     m = re.search(r'(\d{4})', title)
#     producers = re.sub(r'\s*\(.*?\)\s*$', '', title)
#     backup_producers = producers.split(m.group(1))

#     if m:
#         producers = re.split(f"{m.group(1)}|,", producers)
#         for i in range(len(producers)):
#             producers[i] = producers[i].strip()
#             if not producers[i]:
#                 del producers[i]
                
#         for backup in backup_producers:
#             if backup:
#                 backup = backup.strip()
#                 producers.append(backup)

#         return producers
#     return None
    
# def match_region_and_country(strings, df):
#     # df = pd.read_excel(r"../../spiders/LWIN wines.xls")
#     best_string = None
#     best_indices = None
#     best_count = 0

#     for s in strings:
#         mask = df['Wine'].str.contains(s, case=False, na=False) | df['Estate'].str.contains(s, case=False, na=False)
#         matching_indices = df.index[mask]
#         count = len(matching_indices)
#         if count > best_count:
#             best_count = count
#             best_string = s
#             best_indices = matching_indices

#     if best_count == 0:
#         raise NoMatchedRegionAndCountryException(f"No matched region or country for {strings}")

#     counter = Counter()
#     for i in best_indices:
#         pair = (df.loc[i, 'Region'], df.loc[i, 'Country'])
#         counter[pair] += 1

#     most_common = counter.most_common()
#     if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
#         raise AmbiguousRegionAndCountryMatchException(
#             f"Ambiguous region and country match for string '{best_string}': {most_common}"
#         )

#     return most_common[0][0]

def clean_title(title):
    title = re.sub(r'\s*\(.*?\)\s*$', '', title)
    title = re.sub(r'\b\d{4}\b', ',', title)
    return title.strip()

def match_lot_info(title, df):
    # df = pd.read_excel(r"../../spiders/LWIN wines.xls")
    cleaned_title = clean_title(title)
    producer_matches = set()
    for idx, producer in enumerate(df['Estate']):
        if producer.lower() in cleaned_title.lower():
            producer_matches.add((df.loc[idx, 'Estate'],df.loc[idx, 'Region'], df.loc[idx, 'Country']))

    if len(producer_matches) == 1:
        return producer_matches.pop()
    elif len(producer_matches) > 1:
        raise AmbiguousRegionAndCountryMatchException(title)
    
    wine_matches = Counter()
    for idx, wine in enumerate(df["Wine"]):
        if cleaned_title.lower() in wine.lower():
            pair = (df.loc[idx, "Estate"], df.loc[idx, "Region"], df.loc[idx, "Country"])
            wine_matches[pair] += 1

    if not wine_matches:
        cleaned_title_strings = cleaned_title.lower().replace(',', '').strip().split(' ')
        cleaned_title_strings.extend(cleaned_title.lower().replace(',', '').strip())
        for idx, wine in enumerate(df["Wine"]):
            match_count = sum(1 for cleaned_title_string in cleaned_title_strings if cleaned_title_string in wine.lower())
            if match_count / len(cleaned_title_strings) >= 0.5:
                pair = (df.loc[idx, "Estate"], df.loc[idx, "Region"], df.loc[idx, "Country"])
                wine_matches[pair] += 1

    if not wine_matches:
        raise NoMatchedRegionAndCountryException(title)
    most_common = wine_matches.most_common()
    if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
        raise AmbiguousRegionAndCountryMatchException(title)
    return most_common[0][0]


# titles = [
#     "Château Lafite 1964  (12 BT)",
#     "Beaune Premier Cru, Cuvée Guigone de Salins 2024  (1 PCE)",
#     "Château Margaux 1982  (12 BT)",
#     "Château Gazin 1990  (12 BT)",
#     "Volnay Premier Cru Les Santenots, Cuvée Jéhan de Massol 2024  (1 PCE)",
#     "Petrus 1982  (6 MAG)",
#     "Château Pichon Longueville, Lalande 1988  (12 BT)",
#     "Volnay Premier Cru, Cuvée Blondeau 2024  (1 PCE)",
#     "Clos de la Roche, Cuvée William 1988 Domaine Ponsot (12 BT)",
#     "Vosne Romanée, Les Chaumes 2015 Méo-Camuzet (8 BT)"
# ]

# for t in titles:
#     print("----------------------------------------------")
#     print(t, "->", match_lot_info(t))

    