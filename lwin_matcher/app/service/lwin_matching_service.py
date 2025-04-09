import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from app.model import MatchResult
from collections import OrderedDict
from .utils import LwinMatchingUtils
from database.database_client import DatabaseClient
from database.model import LwinDatabaseModel

class LwinMatchingService:
    def __init__(self):
        self.db = DatabaseClient()
        self.sess = self.db.Session()
        self.table = self.db.get_table('lwin_database')

        table_items = pd.read_sql(self.sess.query(self.table).statement, self.sess.bind)
        self.utils = LwinMatchingUtils(
            table_items
        )
        self.table_items = table_items

    def lwin_matching(self, lwinMatchingParams):
        matches = self.calculate_multiple(lwinMatchingParams)
        matches = self.filter_matches(matches, lwinMatchingParams)

        if len(matches) == 0:
            match_result = MatchResult.NOT_MATCH
        elif len(matches) == 1:
            match_result = MatchResult.EXACT_MATCH
        else:
            match_result = MatchResult.MULTI_MATCH
        
        columns = [column.name for column in LwinDatabaseModel.__table__.columns]
        return match_result, [match[0]['lwin'] for match in matches], [match[1] for match in matches], [OrderedDict({columns[i]: match[0].iloc[i] for i in range(len(columns))}) for match in matches]

    def calculate_multiple(self, lwinMatchingParams):
        wine_name_similarities = self.utils.calculate_tfidf_similarity(lwinMatchingParams.wine_name)
        producer_similarities = self.utils.calculate_tfidf_similarity(lwinMatchingParams.lot_producer) if lwinMatchingParams.lot_producer else wine_name_similarities
        total_scores = (wine_name_similarities * 0.7 + producer_similarities * 0.3)

        if total_scores.max() > 0.9:
            total_scores = np.where(total_scores == total_scores.max(), total_scores, 0)
            high_score_indices = np.where(total_scores > 0.9)[0]
        elif total_scores.max() < 0.8:
            total_scores = np.where(total_scores == total_scores.max(), total_scores, 0)
            high_score_indices = np.where(total_scores < 0.8)[0]
        else:
            high_score_indices = np.where(total_scores > 0.8)[0]
        top_matches = self.table_items.iloc[high_score_indices]
        matches = [(row, total_scores[idx]) for idx, row in top_matches.iterrows()]

        return matches
    
    def filter_matches(self, matches, lwinMatchingParams):
        filtered_matches = []

        for match in matches:

            if lwinMatchingParams.country and match[0]['country'] and fuzz.partial_ratio(lwinMatchingParams.country.lower(), match[0]['country'].lower()) < 90:
                continue
            if lwinMatchingParams.region and match[0]['region'] and fuzz.partial_ratio(lwinMatchingParams.region.lower(), match[0]['region'].lower()) < 90:
                continue
            if lwinMatchingParams.sub_region and match[0]['sub_region'] and fuzz.partial_ratio(lwinMatchingParams.sub_region.lower(), match[0]['sub_region'].lower()) < 90:
                continue
            if lwinMatchingParams.colour and match[0]['colour'] and fuzz.partial_ratio(lwinMatchingParams.colour.lower(), match[0]['colour'].lower()) < 90:
                continue

            filtered_matches.append(match)
        
        return filtered_matches