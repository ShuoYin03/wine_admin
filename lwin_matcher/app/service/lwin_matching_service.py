import re
import bm25s
import Stemmer
import numpy as np
from rapidfuzz import fuzz
from collections import OrderedDict
from app.model import MatchResult
from database.model import LwinDatabaseModel

class LwinMatcherEngine:
    def __init__(self, table_items):
        self.table_items = table_items
        self.stemmer = Stemmer.Stemmer("english")

        self.corpus = table_items.apply(self._merge_text_fields, axis=1).apply(self._clean_title).tolist()
        self.tokenized_corpus = bm25s.tokenize(self.corpus, stopwords="en", stemmer=self.stemmer)

        self.retriever = bm25s.BM25()
        self.retriever.index(self.tokenized_corpus)

    # -------------- 外部调用接口 ----------------
    def match(self, lwinMatchingParams, limit=20, topk=1):
        matches = self._bm25_candidates(lwinMatchingParams.wine_name, limit)
        query_cleaned = self._clean_title(lwinMatchingParams.wine_name)

        scored_matches = [
            (row, self._score(row, query_cleaned, bm25_score))
            for row, bm25_score in matches
        ]

        scored_matches.sort(key=lambda x: x[1], reverse=True)
        scored_matches = scored_matches[:topk]

        filtered_matches = self._filter_matches(scored_matches, lwinMatchingParams)
        match_result = self._classify(filtered_matches)

        columns = [col.name for col in LwinDatabaseModel.__table__.columns]
        return (
            match_result,
            [m[0]['lwin'] for m in filtered_matches],
            self._convert_scores([m[1] for m in filtered_matches]),
            [OrderedDict({columns[i]: m[0].iloc[i] for i in range(len(columns))}) for m in filtered_matches]
        )
    
    def match_target_by_id(self, lwinMatchingParams, record_id):
        target_idx = self.table_items[self.table_items['id'] == record_id].index[0]
        return self.match_target(lwinMatchingParams, target_idx)

    def match_target(self, lwinMatchingParams, target_idx):
        query_cleaned = self._clean_title(lwinMatchingParams.wine_name)
        query_tokens = bm25s.tokenize([lwinMatchingParams.wine_name], stopwords="en", stemmer=self.stemmer)
        results, scores = self.retriever.retrieve(query_tokens, k=len(self.table_items))
        score_dict = dict(zip(results[0], scores[0]))
        bm25_score = score_dict.get(target_idx, 0)

        target_row = self.table_items.iloc[target_idx]
        print(f"Target row: {target_row['display_name']}")
        wine_cleaned = self._clean_title(target_row['display_name'])
        fuzz_score = fuzz.token_set_ratio(query_cleaned, wine_cleaned)

        return 0.7 * (bm25_score / (bm25_score + 1e-5)) + 0.3 * (fuzz_score / 100)

    # -------------- 内部 BM25 检索 ----------------
    def _bm25_candidates(self, title, limit):
        if not title:
            return []
        query_tokens = bm25s.tokenize([title], stopwords="en", stemmer=self.stemmer)
        results, scores = self.retriever.retrieve(query_tokens, k=limit)
        return [(self.table_items.iloc[idx], score) for idx, score in zip(results[0], scores[0])]

    # -------------- 内部匹配评分逻辑 ----------------
    def _score(self, row, query_cleaned, bm25_score):
        wine_cleaned = self._clean_title(row['display_name'])
        fuzz_score = fuzz.token_set_ratio(query_cleaned, wine_cleaned)
        return 0.7 * (bm25_score / (bm25_score + 1e-5)) + 0.3 * (fuzz_score / 100)

    def _filter_matches(self, matches, params):
        filtered = []
        for row, score in matches:
            if self._passes_filters(row, params):
                filtered.append((row, score))
        return filtered

    def _passes_filters(self, row, params):
        filters = [
            (params.lot_producer, row.get('producer_name')),
            (params.country, row.get('country')),
            (params.region, row.get('region')),
            (params.sub_region, row.get('sub_region')),
            (params.colour, row.get('colour')),
        ]
        for param_val, row_val in filters:
            if param_val and row_val:
                if fuzz.partial_ratio(param_val.lower(), row_val.lower()) < 90:
                    return False
        return True

    def _classify(self, matches):
        if not matches:
            return MatchResult.NOT_MATCH
        if len(matches) == 1:
            return MatchResult.EXACT_MATCH
        return MatchResult.MULTI_MATCH

    # -------------- 清洗预处理逻辑 ----------------
    def _clean_title(self, title):
        if not title:
            return ''
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)
        title = re.sub(r'\b\d{4}\b', '', title)
        title = re.sub(r'[^\w\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title.lower().strip()

    def _merge_text_fields(self, row):
        return ' '.join(filter(None, [
            row.get('display_name', ''),
            row.get('producer_title', ''),
            row.get('producer_name', ''),
            row.get('wine', '')
        ]))

    def _convert_scores(self, obj):
        for i in range(len(obj)):
            if isinstance(obj[i], (np.float64, np.float32)):
                obj[i] = float(obj[i])
            elif isinstance(obj[i], (np.int64, np.int32)):
                obj[i] = int(obj[i])
        return obj
