import pandas as pd
from rapidfuzz import fuzz
from app.model import MatchResult
from flask import current_app, g
from collections import OrderedDict
from .utils import LwinMatchingUtils
from database.model import LwinDatabaseModel

class LwinMatchingService:
    def __init__(self, table_items):
        self.utils = LwinMatchingUtils(table_items)
        
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
        return match_result, \
            [match[0]['lwin'] for match in matches], \
            self.utils.convert_to_serializable([match[1] for match in matches]), \
            [OrderedDict({columns[i]: match[0].iloc[i] for i in range(len(columns))}) for match in matches]

    def calculate_multiple(self, lwinMatchingParams):
        matches = self.utils.search_by_bm25(lwinMatchingParams.wine_name, limit=20)

        improved_matches = []
        query_cleaned = self.utils.clean_title(lwinMatchingParams.wine_name)

        for row, bm25_score in matches:
            wine_name = row['display_name']
            wine_name_cleaned = self.utils.clean_title(wine_name)

            fuzz_score = fuzz.token_set_ratio(query_cleaned, wine_name_cleaned)

            final_score = 0.7 * (bm25_score / (bm25_score + 1e-5)) + 0.3 * (fuzz_score / 100)

            improved_matches.append((row, final_score))

        improved_matches.sort(key=lambda x: x[1], reverse=True)

        improved_matches = improved_matches[:1]

        return [(row, score) for row, score in improved_matches]
    
    def filter_matches(self, matches, lwinMatchingParams):
        filtered_matches = []

        for match in matches:
            if lwinMatchingParams.lot_producer and match[0]['producer_name'] and fuzz.partial_ratio(lwinMatchingParams.lot_producer.lower(), match[0]['producer_name'].lower()) < 90:
                continue
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


    def match_target(self, lwinMatchingParams, target_record):
        query_cleaned = self.utils.clean_title(lwinMatchingParams.wine_name)
        query_tokens = bm25s.tokenize([lwinMatchingParams.wine_name], stopwords="en", stemmer=self.utils.stemmer)

        results, scores = self.utils.retriever.retrieve(query_tokens, k=len(self.utils.table_items))

        # 拿 target_idx 对应的 BM25 score
        bm25_score = 0
        for idx, score in zip(results[0], scores[0]):
            if idx == target_idx:
                bm25_score = score
                break

        # 取出 target_record
        target_record = self.utils.table_items.iloc[target_idx]

        # fuzzy 计算
        wine_name_cleaned = self.utils.clean_title(target_record['display_name'])
        fuzz_score = fuzz.token_set_ratio(query_cleaned, wine_name_cleaned)

        # 综合评分
        final_score = 0.7 * (bm25_score / (bm25_score + 1e-5)) + 0.3 * (fuzz_score / 100)

        return final_score