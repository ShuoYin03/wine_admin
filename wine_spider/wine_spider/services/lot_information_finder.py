import re
import os
import pandas as pd
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from wine_spider.exceptions import (
    AmbiguousRegionAndCountryMatchException,
    NoMatchedRegionAndCountryException
)

class LotInformationFinder:
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        excel_path = os.path.join(base_dir, r"LWIN wines.xls")
        self.df = pd.read_excel(excel_path)
        
    def clean_title(self, title):
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)
        title = re.sub(r'\b\d{4}\b', '', title)
        title = re.sub(r'[^\w\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        title = title.lower().strip()
        return title

    def standardize_title(self, title):
        replace_dict = {
            "Leoville": "Léoville",
        }
        
        for key, value in replace_dict.items():
            title = title.replace(key, value)
        return title

    def find_lot_information(self, title):
        wine_column = 'Wine'
        producer_column = 'Estate'
        region_column = 'Region'
        sub_region_column = 'subRegion'
        country_column = 'Country'
        combined_score_column = 'combined_score'

        cleaned_title = self.clean_title(title)
        
        wine_sim_scores = self.calculate_tfidf_similarity(cleaned_title, self.df[wine_column])
        fuzzy_scores = self.df[wine_column].apply(lambda x: self.fuzzy_score(cleaned_title, x))
        producer_scores = self.df[producer_column].apply(lambda x: self.fuzzy_score(cleaned_title, x))
        sub_region_scores = self.df[sub_region_column].apply(lambda x: self.fuzzy_score(cleaned_title, x))
        
        self.df['combined_score'] = (
            wine_sim_scores * 0.4 +   # 40% weight for wine name similarity
            fuzzy_scores * 0.2 +      # 20% weight for fuzzy match
            producer_scores * 0.2 +     # 20% weight for producer name match
            sub_region_scores * 0.2     # 20% weight for sub region match
        )

        max_score = self.df['combined_score'].max()
        best_match = self.df[self.df['combined_score'] == max_score]
        if len(best_match) > 1:
            raise AmbiguousRegionAndCountryMatchException(title)
        best_match = best_match.iloc[0]

        if best_match['combined_score'] > 40:
            return (best_match[producer_column], 
                    best_match[region_column], 
                    best_match[sub_region_column], 
                    best_match[country_column])
        else:
            raise NoMatchedRegionAndCountryException(title, best_match[wine_column], best_match[producer_column], best_match[region_column], best_match[sub_region_column], best_match[country_column], best_match[combined_score_column])

    def calculate_tfidf_similarity(self, title, df_column):
        vectorizer = TfidfVectorizer()
        df_column = df_column.fillna("").apply(self.clean_title)
        tfidf_matrix = vectorizer.fit_transform([title] + df_column.fillna("").tolist())
        cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        return cosine_similarities

    def fuzzy_score(self, title, target):
        if isinstance(target, str):
            return fuzz.token_set_ratio(self.clean_title(title), self.clean_title(target))
        return 0

if __name__ == "__main__":
    lot_information_finder = LotInformationFinder()
    title = "Château Lafite-Rothschild 2003 (6 Bottles)"
    try:
        producer, region, sub_region, country = lot_information_finder.find_lot_information(title)
        print(f"Producer: {producer}, Region: {region}, Sub-region: {sub_region}, Country: {country}")
    except (AmbiguousRegionAndCountryMatchException, NoMatchedRegionAndCountryException) as e:
        print(e)