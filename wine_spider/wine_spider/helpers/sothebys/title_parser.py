import re
import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wine_spider.exceptions import AmbiguousRegionAndCountryMatchException, NoMatchedRegionAndCountryException, NoPreDefinedVolumeIdentifierException
from logging import getLogger

logger = getLogger(__name__)

VOLUMN_IDENTIFIER = {
    'bt': 750,
    'bts': 750,
    'hb': 375,
    'hbs': 375,
    'mag': 1500,
    'mags': 1500,
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
    'pce': 228000
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
    
    if volumn == 0.0:
        raise NoPreDefinedVolumeIdentifierException(title)
    
    return volumn, qty


def parse_year_from_title(title):
    m = re.search(r'(\d{4})-(\d{4})', title)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{4})\b', title)
    if m:
        return int(m.group(1))
    return None

def clean_title(title):
    title = re.sub(r'\s*\(.*?\)\s*$', '', title)
    title = re.sub(r'\b\d{4}\b', '', title)
    title = re.sub(r'[^\w\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = title.lower().strip()
    return title

def standardize_title(title):
    replace_dict = {
        "Leoville": "Léoville",
    }
    
    for key, value in replace_dict.items():
        title = title.replace(key, value)
    return title

def match_lot_info(title, df):
    wine_column = 'Wine'
    producer_column = 'Estate'
    region_column = 'Region'
    sub_region_column = 'subRegion'
    country_column = 'Country'
    combined_score_column = 'combined_score'

    cleaned_title = clean_title(title)
    
    wine_sim_scores = calculate_tfidf_similarity(cleaned_title, df[wine_column])
    fuzzy_scores = df[wine_column].apply(lambda x: fuzzy_score(cleaned_title, x))
    producer_scores = df[producer_column].apply(lambda x: fuzzy_score(cleaned_title, x))
    sub_region_scores = df[sub_region_column].apply(lambda x: fuzzy_score(cleaned_title, x))
    
    df['combined_score'] = (
        wine_sim_scores * 0.4 +   # 40% weight for wine name similarity
        fuzzy_scores * 0.2 +      # 20% weight for fuzzy match
        producer_scores * 0.2 +     # 20% weight for producer name match
        sub_region_scores * 0.2     # 20% weight for sub region match
    )

    max_score = df['combined_score'].max()
    best_match = df[df['combined_score'] == max_score]
    if len(best_match) > 1:
        raise AmbiguousRegionAndCountryMatchException(title)
    best_match = best_match.iloc[0]

    if best_match['combined_score'] > 40:
        return (best_match[producer_column], 
                best_match[region_column], 
                best_match[sub_region_column], 
                best_match[country_column])
    else:
        logger.debug(f"Best match: {best_match[wine_column]} {best_match[producer_column]} {best_match[region_column]} {best_match[sub_region_column]} {best_match[country_column]} {best_match[combined_score_column]}")
        raise NoMatchedRegionAndCountryException(title)

def calculate_tfidf_similarity(title, df_column):
    vectorizer = TfidfVectorizer()
    df_column = df_column.fillna("").apply(clean_title)
    tfidf_matrix = vectorizer.fit_transform([title] + df_column.fillna("").tolist())
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    return cosine_similarities

def fuzzy_score(title, target):
    if isinstance(target, str):
        return fuzz.token_set_ratio(clean_title(title), clean_title(target))
    return 0

# def match_lot_info(title, df):
#     cleaned_title = clean_title(title)
#     print("Cleaned title:", cleaned_title)

#     # Special Case Exact match
#     lot_producer, region, sub_region, country = special_case_exact_match(cleaned_title)
    
#     if not lot_producer:
#         # Producer Exact Match
#         producer_exact_match_indices = producer_exact_match(cleaned_title, df['Estate'])
#         filtered_df = filter_df_by_index(df, producer_exact_match_indices)
#         # print("Filtered DF:", len(filtered_df))
#         if len(filtered_df) == 1:
#             return filtered_df.iloc[0]['Estate'], filtered_df.iloc[0]['Region'], filtered_df.iloc[0]['subRegion'], filtered_df.iloc[0]['Country']
#         elif len(filtered_df) > 1:
#             # Wine Name Exact Match
#             idx = wine_exact_match(cleaned_title, filtered_df['Wine'])
#             if idx:
#                 return filtered_df.iloc[idx]['Estate'], filtered_df.iloc[idx]['Region'], filtered_df.iloc[idx]['subRegion'], filtered_df.iloc[idx]['Country']
#             lot_producer, region, sub_region, country = wine_fuzzy_match(cleaned_title, filtered_df)
#             return lot_producer, region, sub_region, country
#         else:
#             # Wine Name & Producer Fuzzy Match
#             lot_producer, region, sub_region, country = wine_and_producer_fuzzy_match(cleaned_title, df)
#             return lot_producer, region, sub_region, country
            
#     else:
#         # Wine Name Exact Match
#         idx = wine_exact_match(cleaned_title, filtered_df['Wine'])
#         if idx:
#             return filtered_df.iloc[idx]['Estate'], filtered_df.iloc[idx]['Region'], filtered_df.iloc[idx]['subRegion'], filtered_df.iloc[idx]['Country']
#         lot_producer, region, sub_region, country = wine_fuzzy_match(cleaned_title, filtered_df)
#         return lot_producer, region, sub_region, country

# def filter_df_by_index(df, indices):
#     return df.iloc[indices]

# def special_case_exact_match(title):
#     if 'drc' in title.lower() or 'domaine de la romanée conti' in title.lower():
#         return "Domaine de la Romanée-Conti", "Burgundy", None, "France"
#     return None, None, None, None

# def producer_exact_match(title, producer_df_column):
#     indices = []
#     for idx, producer in enumerate(producer_df_column):
#         if producer.lower() in title or title in producer.lower():
#             indices.append(idx)
    
#     return indices

# def wine_exact_match(title, wine_df_column):
#     for idx, wine in enumerate(wine_df_column):
#         if title in wine.lower() or wine.lower() in title:
#             return idx
    
#     return None

# def wine_fuzzy_match(title, df):
#     matches = []

#     for row in df.itertuples():
#         idx = row.Index
#         wine_score = fuzz.partial_token_sort_ratio(row.Wine.replace("-", " ").lower(), title)
#         if wine_score > 80:
#             matches.append((idx, wine_score))
    
#     matches.sort(key=lambda x: x[1], reverse=True)

#     if not matches:
#         return None, None, None, None
#     else:
#         idx = matches[0][0]
#         return df.loc[idx, "Estate"], df.loc[idx, "Region"], df.loc[idx, 'subRegion'], df.loc[idx, "Country"]

# def wine_and_producer_fuzzy_match(title, df):
#     matches = []

#     for row in df.itertuples():
#         idx = row.Index
#         producer_score = fuzz.token_ratio(row.Estate.lower(), title)
#         wine_score = fuzz.partial_token_sort_ratio(title, row.Wine.replace("-", " ").lower())
#         added_score = (producer_score * 0.3 + wine_score * 0.7) / 2
#         if added_score > 30:
#             matches.append((idx, added_score, producer_score, wine_score))
    
#     matches.sort(key=lambda x: x[1], reverse=True)

#     if not matches:
#         return None, None, None, None
#     else:
#         idx = matches[0][0]
#         return df.loc[idx, "Estate"], df.loc[idx, "Region"], df.loc[idx, 'subRegion'], df.loc[idx, "Country"]

if __name__ == "__main__":
    df = pd.read_excel(r"LWIN wines.xls")
    print(match_lot_info("Château Gazin 1989  (12 BT)", df))