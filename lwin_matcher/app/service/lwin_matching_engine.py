import re
import os
import math
import bm25s
import pickle
import Stemmer
import numpy as np
import pandas as pd
import unicodedata
from rapidfuzz import fuzz
from collections import OrderedDict
from lwin_matcher.app.model import MatchResult
from shared.database.model import LwinDatabaseModel
    
class LwinMatcherEngine:
    def __init__(self, table_items, cache_dir="./.bm25_cache"):
        self.table_items = table_items
        self.stemmer = Stemmer.Stemmer("english")

        os.makedirs(cache_dir, exist_ok=True)
        token_path = os.path.join(cache_dir, "tokenized_corpus.pkl")
        index_path = os.path.join(cache_dir, "bm25_index.pkl")

        if os.path.exists(token_path) and os.path.exists(index_path):
            with open(token_path, "rb") as f:
                self.tokenized_corpus = pickle.load(f)
            with open(index_path, "rb") as f:
                self.retriever = pickle.load(f)
        else:
            self.corpus = table_items.apply(self._merge_text_fields, axis=1).apply(self._clean_title).tolist()
            self.tokenized_corpus = bm25s.tokenize(self.corpus, stopwords="en", stemmer=self.stemmer)

            self.retriever = bm25s.BM25()
            self.retriever.index(self.tokenized_corpus)

            with open(token_path, "wb") as f:
                pickle.dump(self.tokenized_corpus, f)
            with open(index_path, "wb") as f:
                pickle.dump(self.retriever, f)

    # -------------- Public Interface ----------------
    def match(self, lwinMatchingParams, limit=10, topk=1):
        query_cleaned = self._clean_title(lwinMatchingParams.wine_name)
        producer_cleaned = self._clean_title(lwinMatchingParams.lot_producer)
        matches = self._bm25_candidates(query_cleaned, limit)

        scored_matches = [
            (row, self._score(row, query_cleaned, bm25_score))
            for row, bm25_score in matches
        ]

        scored_matches = self._rerank_main_label_priority(scored_matches, query_cleaned, producer_cleaned)
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        # with open("debug_scores.txt", "w", encoding="utf-8") as f:
        #     for row, score in scored_matches:
        #         dump = {
        #             "id": row['id'],
        #             "score": score,
        #             **row.to_dict(),
        #         }
        #         dump = to_native(dump)
        #         json.dump(dump, f, ensure_ascii=False)
        #         f.write("\n")
        scored_matches = scored_matches[:topk]

        filtered_matches = self._filter_matches(scored_matches, lwinMatchingParams)
        match_result = self._classify(filtered_matches)

        columns = [col.name for col in LwinDatabaseModel.__table__.columns]
        return (
            match_result,
            [m[0]['lwin'] if m[0]['reference'] is None else int(math.floor(float(m[0]['reference']))) for m in filtered_matches],
            self._convert_scores([m[1] for m in filtered_matches]),
            [m[0][columns].to_dict(into=OrderedDict) for m in filtered_matches]
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
        wine_cleaned = self._clean_title(target_row['display_name'])
        fuzz_score = fuzz.WRatio(query_cleaned, wine_cleaned)

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
        
        fuzz_score = fuzz.WRatio(query_cleaned, wine_cleaned)

        return 0.7 * (bm25_score / (bm25_score + 1e-5)) + 0.3 * (fuzz_score / 100)

    def _filter_matches(self, matches, params):
        filtered = []
        for row, score in matches:
            if self._passes_filters(row, params):
                filtered.append((row, score))
        return filtered

    def _rerank_main_label_priority(self, scored_matches, lot_name_cleaned, producer_cleaned):
        sub_keywords = [
            "pavillon", "rouge", "blanc", " du ", "assortment", "trilogie", "confidence", "second vin", "dna",
            "grapillons", "petit", "carruades", "les fort", "anaperenna"
        ]

        has_sub_kw = any(k in lot_name_cleaned for k in sub_keywords)

        reranked = []
        for row, score in scored_matches:
            label = (row.get('classification') or '').lower()
            wine_name = (row.get('wine') or '').lower()
            producer = (row.get('producer_name') or '').lower()

            lot_producer = producer_cleaned.lower()
            if lot_producer:
                producer_score = fuzz.partial_ratio(producer, lot_producer) / 100
                if producer_score >= 0.95:
                    score += 0.02
                elif producer_score < 0.80:
                    score -= 0.05

            is_main_label = (
                "premier grand cru" in label or
                "premier cru classe" in label or
                re.search(r"\d+eme cru classe", label)
            )
            is_sub_label = any(k in wine_name for k in sub_keywords) or any(k in (row.get("display_name") or "").lower() for k in sub_keywords)
            
            if not has_sub_kw:
                if is_main_label:
                    score += 0.02
                elif is_sub_label:
                    score -= 0.02

            score = max(0, score)
            reranked.append((row, score))
        return reranked

    def _passes_filters(self, row, params):
        fuzzy_filters = [
            (params.lot_producer, row.get('producer_name')),
            (params.country, row.get('country')),
            (params.region, row.get('region')),
            (params.sub_region, row.get('sub_region')),
        ]

        for param_val, row_val in fuzzy_filters:
            if param_val and row_val:
                if fuzz.partial_ratio(param_val.lower(), row_val.lower()) < 90:
                    return False
        
        exact_filters = [
            (params.colour, row.get('colour')),
        ]
                
        for param_val, row_val in exact_filters:
            if param_val and row_val:
                if (param_val.lower() == "red" or param_val.lower() == "white") and param_val.lower() != row_val.lower():
                    return False
                
        return True

    def _classify(self, matches):
        if not matches:
            return MatchResult.NOT_MATCH
        if len(matches) == 1:
            return MatchResult.EXACT_MATCH
        return MatchResult.MULTI_MATCH

    # -------------- 清洗预处理逻辑 ----------------
    def _clean_title(self, title: str) -> str:
        if not title:
            return ''
        # Normalise unicode and strip accents
        norm = unicodedata.normalize('NFKD', title)
        norm = ''.join(ch for ch in norm if not unicodedata.combining(ch))
        title = norm
        # Remove trailing parenthesised text
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)
        # Remove standalone 4‑digit vintages
        title = re.sub(r'\b\d{4}\b', '', title)
        # Lowercase for uniformity
        title = title.lower()
        # Expand common abbreviations
        abbreviations = {
            'st.': 'saint', 'st ': 'saint ', 'ste.': 'sainte',
            'ch.': 'chateau', "d'": 'de ', 'd’': 'de ',
        }
        for abbr, full in abbreviations.items():
            title = title.replace(abbr, full)
        # Remove common noise words (quality descriptors, packaging, etc.)
        noise_terms = [
            'nv', 'abv', 'bt', 'bts', 'btl', 'bottle', 'bottles', 'magnum', 'magnums', 'balthazar',
            'fine', 'reserve', 'brut', 'extra brut', 'extra-dry', 'sec', 'demi-sec', 'vintage', 'millésime',
            'millesime', 'cuvee', 'assemblage', 'merlot',
        ]
        # Remove any occurrences of noise terms as whole words
        for term in noise_terms:
            title = re.sub(r'\b' + re.escape(term) + r'\b', ' ', title)
        # Replace non‑alphanumeric characters with spaces
        title = re.sub(r'[^\w\s]', ' ', title)
        # Collapse multiple whitespace

        title = re.sub(r'\s+', ' ', title)
        return title.strip()

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
    
    # def _to_native(self, obj):
    #     if isinstance(obj, dict):
    #         return {k: self._to_native(v) for k, v in obj.items()}
    #     elif isinstance(obj, list):
    #         return [self._to_native(v) for v in obj]
    #     elif isinstance(obj, (np.integer, np.int32, np.int64)):
    #         return int(obj)
    #     elif isinstance(obj, (np.floating, np.float32, np.float64)):
    #         return float(obj)
    #     elif isinstance(obj, (np.ndarray,)):
    #         return obj.tolist()
    #     elif obj is np.nan:
    #         return None
    #     elif isinstance(obj, pd.Timestamp):
    #         return obj.isoformat()
    #     else:
    #         return obj