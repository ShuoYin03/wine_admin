import re
import os
import math
import json
import bm25s
import pickle
import Stemmer
import numpy as np
import unicodedata
import pandas as pd
from rapidfuzz import fuzz
from collections import OrderedDict
from app.utils.map_wine_name import map_wine_name
from app.utils.standardize_text import standardize_text
from shared.database.models.lwin_database_db import LwinDatabaseModel
from app.models.match_result import MatchResult
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.matching_rules.matching_context import MatchingContext
from app.service.matching_rules.bordeaux_rule import BordeauxRule
from app.service.matching_rules.burgundy_rule import BurgundyRule
from app.service.matching_rules.colour_should_match_rule import ColourShouldMatchRule
from app.service.matching_rules.not_assortment_case_rule import NotAssortmentCaseRule
from app.service.matching_rules.fuzzy_score_should_above_threshold_rule import FuzzyScoreShouldAboveThresholdRule
from app.service.matching_rules.mixed_lots_should_not_match_rule import MixedLotsShouldNotMatchRule
from app.service.matching_rules.wine_category_should_exist_in_name_rule import WineCategoryShouldExistInNameRule
from app.service.matching_rules.site_should_exist_in_name_rule import SiteShouldExistInNameRule
from app.service.matching_rules.miss_producer_should_not_match_rule import MissProducerShouldNotMatchRule
    
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
    def match(self, lwinMatchingParams: LwinMatchingParams, limit=50, topk=1):
        query_cleaned = self._clean_title(lwinMatchingParams.wine_name)
        lwinMatchingParams.wine_name = query_cleaned
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
        #         dump = self._to_native(dump)
        #         json.dump(dump, f, ensure_ascii=False)
        #         f.write("\n")
        filtered_matches = self._filter_matches(scored_matches, lwinMatchingParams)
        filtered_matches = filtered_matches[:topk]

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

    def _bm25_candidates(self, title, limit):
        if not title:
            return []
        query_tokens = bm25s.tokenize([title], stopwords="en", stemmer=self.stemmer)
        results, scores = self.retriever.retrieve(query_tokens, k=limit)
        return [(self.table_items.iloc[idx], score) for idx, score in zip(results[0], scores[0])]

    def _score(self, row, query_cleaned, bm25_score):
        wine_cleaned = self._clean_title(row['display_name'])
        mapped_wine_cleaned = map_wine_name(wine_cleaned)

        fuzz_score = fuzz.WRatio(query_cleaned, wine_cleaned)
        mapped_wine_fuzz_score = fuzz.WRatio(query_cleaned, mapped_wine_cleaned)

        bm25_norm = math.log1p(bm25_score) / (math.log1p(bm25_score) + 1.0)

        weighted_fuzz_score = 0.7 * bm25_norm + 0.3 * (fuzz_score / 100)
        weighted_mapped_wine_fuzzy_score = 0.7 * bm25_norm + 0.3 * (mapped_wine_fuzz_score / 100)

        return max(weighted_fuzz_score, weighted_mapped_wine_fuzzy_score)

    def _filter_matches(self, matches, params):
        filtered = []
        for row, score in matches:
            if self._passes_filters(row, params):
                filtered.append((row, score))
        return filtered

    def _rerank_main_label_priority(self, scored_matches, lot_name_cleaned, producer_cleaned):
        sub_keywords = [
            "carruades", "les forts", "pavillon", "petit mouton", "petit cheval", "clarence", "carillon", 
            "alter ego", "clos du marquis", "la dame", "les pagodes", "les griffons", "les tourelles", 
            "echo", "le marquis", "second vin", "second wine", "2nd wine", "l'ame de"
        ]

        lot_has_sub_kw = any(k in lot_name_cleaned for k in sub_keywords)

        reranked = []
        for row, score in scored_matches:
            row_label = (row.get('classification') or '').lower()
            row_wine_name = (row.get('wine') or '').lower()
            row_producer = (row.get('producer_name') or '').lower()

            lot_producer = producer_cleaned.lower()
            if lot_producer:
                producer_score = fuzz.WRatio(row_producer, lot_producer) / 100
                if producer_score >= 0.95:
                    score += 0.02
                elif producer_score < 0.80:
                    score -= 0.05

            row_is_main_label = (
                "premier grand cru" in row_label or
                "premier cru classe" in row_label or
                "premier cru" in row_label or
                re.search(r"\d+eme cru classe", row_label)
            )
            row_is_sub_label = any(k in row_wine_name for k in sub_keywords) or any(k in (row.get("display_name") or "").lower() for k in sub_keywords)
            
            if not lot_has_sub_kw:
                if row_is_main_label:
                    score += 0.02
                elif row_is_sub_label:
                    score -= 0.02

            row_sub_region = standardize_text(row.get('sub_region') or '') if row.get('sub_region') else ''
            if row_sub_region and fuzz.WRatio(lot_name_cleaned, row_sub_region) >= 90:
                score += 0.04

            row_site = standardize_text(row.get('site') or '') if row.get('site') else ''
            if row_site and fuzz.WRatio(lot_name_cleaned, row_site) >= 80:
                score += 0.02

            score = max(0, score)
            reranked.append((row, score))
        return reranked

    def _passes_filters(self, row, params: LwinMatchingParams):
        rule = ColourShouldMatchRule() & \
                NotAssortmentCaseRule() & \
                MixedLotsShouldNotMatchRule() & \
                MissProducerShouldNotMatchRule() & \
                BordeauxRule() & \
                BurgundyRule()
                # (WineCategoryShouldExistInNameRule() or \
                # SiteShouldExistInNameRule())
        # else:
            # rule &= FuzzyScoreShouldAboveThresholdRule()

        ctx = MatchingContext(row=row, params=params)
        if not rule.is_satisfied_by(ctx):
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
        if not title or not isinstance(title, str):
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
            'st.': 'saint', 
            'st ': 'saint ', 
            'ste.': 'sainte',
            'ste ': 'sainte ',
            'ch.': 'chateau',
            'ch ': 'chateau ',
            "d'": 'de ', 
            "d’": 'de ',
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
    
    def _to_native(self, obj):
        if isinstance(obj, dict):
            return {k: self._to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._to_native(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif obj is np.nan:
            return None
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        else:
            return obj