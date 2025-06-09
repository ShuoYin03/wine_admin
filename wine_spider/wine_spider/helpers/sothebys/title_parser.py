import re
from rapidfuzz import fuzz
from logging import getLogger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wine_spider.exceptions import (
    AmbiguousRegionAndCountryMatchException, 
    NoMatchedRegionAndCountryException, 
    NoPreDefinedVolumeIdentifierException,
    WrongMatchedRegionAndCountryException,
    NoVolumnInfoException
)
from ..static import VOLUME_IDENTIFIER

logger = getLogger(__name__)

def parse_volume_and_unit_from_title(title):
    volume = 0.0
    potential_volume_strings = re.findall(r'\((.*?)\)', title)

    if not potential_volume_strings:
        if 'MIXED LOT' in title:
            title = title.replace('MIXED LOT ', '').split(' and ')
            for t in title:
                count, identifier = t.split(' ')[0], t.split(' ')[1]
                volume += int(count) * VOLUME_IDENTIFIER[identifier.lower()]
            return volume, int(count)
        raise NoVolumnInfoException(title)
    
    for volume_string in potential_volume_strings:
        tokens = re.split(r',\s*', volume_string)
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            # 2.5 BT or 2.5 BT75cl
            if re.match(r'^(\d+\.?\d*)\s*(.*)$', token):
                m = re.match(r'^(\d+\.?\d*)\s*(.*)$', token)
                qty = float(m.group(1))
                desc = m.group(2).strip()
            elif re.match(r'^(\d+)\s*(.*)$', token):
                m = re.match(r'^(\d+)\s*(.*)$', token)
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
                vol = VOLUME_IDENTIFIER['bt']
                matched = True

            # --- Bottle with leading B and digits (e.g., "B757") ---
            if not matched and re.fullmatch(r'b\d+', desc_lower):
                m_b = re.fullmatch(r'b(\d+)', desc_lower)
                if m_b:
                    vol = float(m_b.group(1))
                    matched = True
            
            # --- Fixed keywords: HFLT, MAG, etc. ---
            if not matched and desc_lower == 'hflt':
                vol = VOLUME_IDENTIFIER['hflt']
                matched = True
            if not matched and desc_lower == 'mag':
                vol = VOLUME_IDENTIFIER['mag']
                matched = True
            if not matched and desc_lower == 'half-gallon':
                vol = VOLUME_IDENTIFIER['half-gallon']
                matched = True

            # --- Bottle patterns ---
            # "Bottles 75cl" or "Bottle 75cl"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+\d+cl', desc_lower):
                m_bottle_cl = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+)cl', desc_lower)
                if m_bottle_cl:
                    vol = float(m_bottle_cl.group(1)) * 10
                    matched = True

            # "Bottle 37.5cl"
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)cl', desc_lower):
                m_bottle_cl = re.fullmatch(r'(?:bottles?|bottle)\s+(\d+(?:\.\d+)?)cl', desc_lower)
                if m_bottle_cl:
                    num = float(m_bottle_cl.group(1))
                    vol = num * 10
                    matched = True
            # "bt 75"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+)', desc_lower):
                m_bottle = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+)', desc_lower)
                if m_bottle:
                    vol = float(m_bottle.group(1)) * 10
                    matched = True

            # "Bottle Pint"
            if not matched and desc_lower == 'bottle pint' or desc_lower == 'bottles pint' or desc_lower == 'bt pint':
                vol = VOLUME_IDENTIFIER['pint']
                matched = True

            # "Bottle 4/5 Quart"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+/\d+)\s+quart', desc_lower):
                m_bottle_quart = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+/\d+)\s+quart', desc_lower)
                if m_bottle_quart:
                    frac_str = m_bottle_quart.group(1)
                    num, den = frac_str.split('/')
                    frac = float(num) / float(den)
                    vol = frac * VOLUME_IDENTIFIER['quart']
                    matched = True
            # "Bottle 1/5 Gallon"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+/\d+)\s+gallon', desc_lower):
                m_bottle_gallon = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+/\d+)\s+gallon', desc_lower)
                if m_bottle_gallon:
                    frac_str = m_bottle_gallon.group(1)
                    num, den = frac_str.split('/')
                    frac = float(num) / float(den)
                    vol = frac * VOLUME_IDENTIFIER['gallon']
                    matched = True
            # "Bottle 25 Fluid Oz" (optionally "fluid" may be omitted)
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+(?:\.\d+)?)\s*(?:fluid\s*)?(?:oz|ounces|oz\.)', desc_lower):
                m_bottle_oz = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+(?:\.\d+)?)\s*(?:fluid\s*)?(?:oz|ounces|oz\.)', desc_lower)
                if m_bottle_oz:
                    num = float(m_bottle_oz.group(1))
                    vol = num * VOLUME_IDENTIFIER['ounces']
                    matched = True
            if not matched and re.fullmatch(r'(?:bottles?|bottle)\s+(?:litre|l)$', desc_lower):
                vol = VOLUME_IDENTIFIER['litre']
                matched = True
            # "Bottle 1.75 Litre" (or "l")
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+(?:\.\d+)?)\s*(?:litre|l)', desc_lower):
                m_bottle_litre = re.fullmatch(r'(?:bottles?|bottle|bt)\s+(\d+(?:\.\d+)?)\s*(?:litre|l)', desc_lower)
                if m_bottle_litre:
                    num = float(m_bottle_litre.group(1))
                    vol = num * VOLUME_IDENTIFIER['litre']
                    matched = True
            # "Bottle Quart"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+quart', desc_lower):
                vol = VOLUME_IDENTIFIER['quart']
                matched = True
            # "Bottle Half-Pint"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+half[\s-]?pint', desc_lower):
                vol = VOLUME_IDENTIFIER['half-pint']
                matched = True
            # "Bottle Half-Gallon"
            if not matched and re.fullmatch(r'(?:bottles?|bottle|bt)\s+half[\s-]?gallon', desc_lower):
                vol = VOLUME_IDENTIFIER['half-pint']
                matched = True
            # If descriptor is exactly "bottle" or "bottles" (default)
            if not matched and desc_lower in ['bottle', 'bottles']:
                vol = VOLUME_IDENTIFIER['bottle']
                matched = True

            # "Pint" or "Pints"
            if not matched and desc_lower in ['pint', 'pints']:
                vol = VOLUME_IDENTIFIER['pint']
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
                    vol = VOLUME_IDENTIFIER['pint'] + frac * VOLUME_IDENTIFIER['ounces']
                    matched = True
            # "Gallon(s)"
            if not matched and desc_lower in ['gallon', 'gallons']:
                vol = VOLUME_IDENTIFIER['gallon']
                matched = True
            # "Litre" variants
            if not matched and desc_lower in ['litre', 'litres', 'l']:
                vol = VOLUME_IDENTIFIER['litre']
                matched = True
            
            # Fallback: if descriptor exactly matches a key in VOLUME_IDENTIFIER:
            if not matched and desc_lower in VOLUME_IDENTIFIER:
                vol = VOLUME_IDENTIFIER[desc_lower]
                matched = True
           
            volume += qty * vol
    
    if volume == 0.0:
        raise NoPreDefinedVolumeIdentifierException(title)
    
    return volume, qty

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

def match_lot_info(title, df, lot_producer=None, region=None, country=None, throw_exception=True):
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
    if len(best_match) > 1 and throw_exception:
        raise AmbiguousRegionAndCountryMatchException(title)
    best_match = best_match.iloc[0]

    if best_match['combined_score'] > 40:
        return (best_match[producer_column], 
                best_match[region_column], 
                best_match[sub_region_column], 
                best_match[country_column])
    
    if not throw_exception:
        return (None, None, None, None)
    raise NoMatchedRegionAndCountryException(title, best_match[wine_column], best_match[producer_column], best_match[region_column], best_match[sub_region_column], best_match[country_column], best_match[combined_score_column])

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

if __name__ == "__main__":
    # df = pd.read_excel(r"LWIN wines.xls")
    # print(match_lot_info("Château Gazin 1989  (12 BT)", df))
    # print(parse_volume_and_unit_from_title("6 Bottles (75cl) per lot"))
    pass