"""Tests for LwinMatcherEngine.

Strategy: build the engine with a tiny in-memory DataFrame (no DB, no real LWIN file).
The BM25 index is built from those rows — no mocking of bm25s needed.
We then mock os.path.exists to False so the engine always rebuilds (no stale cache).
"""
from __future__ import annotations

import math
import tempfile
from collections import OrderedDict
from unittest.mock import patch

import pandas as pd
import pytest

from app.models.lwin_matching_params import LwinMatchingParams
from app.models.match_result import MatchResult
from app.service.lwin_matching_engine import LwinMatcherEngine


# ── Fixture helpers ─────────────────────────────────────────────────────────

# All columns that LwinDatabaseModel.__table__.columns contains
COLUMNS = [
    "id", "lwin", "status", "display_name", "producer_title", "producer_name",
    "wine", "country", "region", "sub_region", "site", "parcel", "colour",
    "type", "sub_type", "designation", "classification", "vintage_config",
    "first_vintage", "final_vintage", "date_added", "date_updated", "reference",
]


def make_row(**kwargs) -> dict:
    defaults = {
        "id": 1,
        "lwin": 1000001,
        "status": "active",
        "reference": None,
        "display_name": "",
        "producer_title": "",
        "producer_name": "",
        "wine": "",
        "colour": "Red",
        "region": "",
        "sub_region": "",
        "country": "France",
        "site": None,
        "parcel": None,
        "type": "Wine",
        "sub_type": None,
        "designation": None,
        "classification": "",
        "vintage_config": None,
        "first_vintage": None,
        "final_vintage": None,
        "date_added": pd.Timestamp("2020-01-01"),
        "date_updated": pd.Timestamp("2020-01-01"),
    }
    return {**defaults, **kwargs}


def make_engine(rows: list[dict]) -> LwinMatcherEngine:
    df = pd.DataFrame(rows, columns=COLUMNS)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Force rebuild each time by using a fresh temp dir (no cached files)
        engine = LwinMatcherEngine(df, cache_dir=tmpdir)
    return engine


@pytest.fixture
def engine():
    rows = [
        make_row(id=1, lwin=1000001, display_name="Chateau Petrus", producer_name="Petrus",
                 producer_title="Chateau", wine="Petrus", colour="Red",
                 region="Bordeaux", sub_region="Pomerol", country="France"),
        make_row(id=2, lwin=1000002, display_name="Chateau Margaux", producer_name="Margaux",
                 producer_title="Chateau", wine="Margaux", colour="Red",
                 region="Bordeaux", sub_region="Margaux", country="France"),
        make_row(id=3, lwin=1000003, display_name="Chateau Latour", producer_name="Latour",
                 producer_title="Chateau", wine="Latour", colour="Red",
                 region="Bordeaux", sub_region="Pauillac", country="France"),
        make_row(id=4, lwin=1000004, display_name="Opus One", producer_name="Opus One",
                 producer_title="", wine="Opus One", colour="Red",
                 region="Napa Valley", sub_region="", country="USA"),
        make_row(id=5, lwin=1000005, display_name="Pouilly Fume Blanc", producer_name="Dagueneau",
                 producer_title="Didier", wine="Pouilly Fume", colour="White",
                 region="Loire Valley", sub_region="", country="France"),
    ]
    return make_engine(rows)


# ── _clean_title ────────────────────────────────────────────────────────────

class TestCleanTitle:
    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def test_removes_vintage(self):
        assert "2015" not in self.engine._clean_title("Chateau Petrus 2015")

    def test_lowercases(self):
        result = self.engine._clean_title("Chateau PETRUS")
        assert result == result.lower()

    def test_expands_st_abbreviation(self):
        result = self.engine._clean_title("St. Emilion")
        assert "saint" in result

    def test_expands_ch_abbreviation(self):
        result = self.engine._clean_title("Ch. Petrus")
        assert "chateau" in result

    def test_removes_trailing_parentheses(self):
        result = self.engine._clean_title("Petrus (Grand Cru)")
        assert "(" not in result

    def test_removes_noise_terms(self):
        result = self.engine._clean_title("Chateau Petrus Brut Reserve")
        assert "brut" not in result
        assert "reserve" not in result

    def test_empty_string_returns_empty(self):
        assert self.engine._clean_title("") == ""

    def test_none_returns_empty(self):
        assert self.engine._clean_title(None) == ""

    def test_strips_accents(self):
        result = self.engine._clean_title("Pétrus")
        assert "é" not in result
        assert "petrus" in result


# ── _classify ───────────────────────────────────────────────────────────────

class TestClassify:
    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def test_empty_matches_not_match(self):
        assert self.engine._classify([]) == MatchResult.NOT_MATCH

    def test_single_match_exact(self):
        row = pd.Series(make_row())
        assert self.engine._classify([(row, 0.9)]) == MatchResult.EXACT_MATCH

    def test_multiple_matches_multi(self):
        row = pd.Series(make_row())
        assert self.engine._classify([(row, 0.9), (row, 0.8)]) == MatchResult.MULTI_MATCH


# ── _score ───────────────────────────────────────────────────────────────────

class TestScore:
    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def test_score_between_0_and_1(self):
        row = pd.Series(make_row(display_name="Chateau Petrus"))
        score = self.engine._score(row, "chateau petrus", bm25_score=5.0)
        assert 0 <= score <= 1

    def test_exact_match_scores_higher_than_mismatch(self):
        exact_row = pd.Series(make_row(display_name="Chateau Petrus"))
        other_row = pd.Series(make_row(display_name="Chateau Margaux"))
        exact_score = self.engine._score(exact_row, "chateau petrus", bm25_score=5.0)
        other_score = self.engine._score(other_row, "chateau petrus", bm25_score=1.0)
        assert exact_score > other_score

    def test_zero_bm25_score_gives_low_result(self):
        row = pd.Series(make_row(display_name="Chateau Petrus"))
        score = self.engine._score(row, "chateau petrus", bm25_score=0.0)
        # bm25_norm = log1p(0) / (log1p(0) + 1.0) = 0 → score is entirely fuzz-based
        assert score >= 0


# ── match (integration via small corpus) ────────────────────────────────────

CORPUS_SIZE = 5  # number of rows in our test fixture


class TestMatch:
    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def _params(self, wine_name, **kwargs):
        return LwinMatchingParams(wine_name=wine_name, lot_producer=kwargs.pop("lot_producer", "Petrus"), **kwargs)

    def test_match_returns_four_tuple(self):
        params = self._params("Chateau Petrus")
        result = self.engine.match(params, limit=CORPUS_SIZE)
        assert len(result) == 4

    def test_match_result_is_match_result_enum(self):
        params = self._params("Chateau Petrus")
        match_result, *_ = self.engine.match(params, limit=CORPUS_SIZE)
        assert isinstance(match_result, MatchResult)

    def test_lwin_code_is_list(self):
        params = self._params("Chateau Petrus")
        _, lwin_codes, _, _ = self.engine.match(params, limit=CORPUS_SIZE)
        assert isinstance(lwin_codes, list)

    def test_scores_are_floats(self):
        params = self._params("Chateau Petrus")
        _, _, scores, _ = self.engine.match(params, limit=CORPUS_SIZE)
        for s in scores:
            assert isinstance(s, float)

    def test_match_items_are_dicts(self):
        params = self._params("Chateau Petrus")
        _, _, _, items = self.engine.match(params, limit=CORPUS_SIZE)
        for item in items:
            assert isinstance(item, (dict, OrderedDict))

    def test_no_producer_returns_not_match(self):
        params = LwinMatchingParams(wine_name="Chateau Petrus", lot_producer="")
        match_result, lwin_codes, scores, items = self.engine.match(params, limit=CORPUS_SIZE)
        assert match_result == MatchResult.NOT_MATCH
        assert lwin_codes == []

    def test_topk_limits_results(self):
        params = LwinMatchingParams(wine_name="Chateau", lot_producer="Petrus", region="Bordeaux")
        _, _, _, items = self.engine.match(params, limit=CORPUS_SIZE, topk=1)
        assert len(items) <= 1

    def test_mixed_lot_name_returns_not_match(self):
        params = LwinMatchingParams(wine_name="Mixed Case of Bordeaux", lot_producer="Various")
        match_result, *_ = self.engine.match(params, limit=CORPUS_SIZE)
        assert match_result == MatchResult.NOT_MATCH


# ── _filter_matches ──────────────────────────────────────────────────────────

class TestFilterMatches:
    """_filter_matches works on pre-built (row, score) pairs — no BM25 call needed."""

    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def _make_matches(self, rows_and_scores):
        return [(pd.Series(make_row(**r)), s) for r, s in rows_and_scores]

    def test_assortment_row_is_filtered_out(self):
        params = LwinMatchingParams(wine_name="test", lot_producer="Petrus")
        matches = self._make_matches([
            ({"display_name": "Assortment of Bordeaux", "wine": "Assortment"}, 0.9),
            ({"display_name": "Chateau Petrus", "wine": "Petrus"}, 0.8),
        ])
        filtered = self.engine._filter_matches(matches, params)
        assert all("assortment" not in (r.get("display_name") or "").lower() for r, _ in filtered)

    def test_colour_mismatch_is_filtered_out(self):
        params = LwinMatchingParams(wine_name="white wine", lot_producer="Dagueneau", colour="White")
        matches = self._make_matches([
            ({"display_name": "Red Wine", "colour": "Red", "wine": "Red"}, 0.9),
            ({"display_name": "White Wine", "colour": "White", "wine": "White"}, 0.8),
        ])
        filtered = self.engine._filter_matches(matches, params)
        colours = [r.get("colour") for r, _ in filtered]
        assert "Red" not in colours
        assert "White" in colours


# ── _convert_scores ──────────────────────────────────────────────────────────

class TestConvertScores:
    @pytest.fixture(autouse=True)
    def setup(self, engine):
        self.engine = engine

    def test_numpy_float64_becomes_python_float(self):
        import numpy as np
        scores = [np.float64(0.95), np.float32(0.8)]
        result = self.engine._convert_scores(scores)
        for s in result:
            assert type(s) is float

    def test_numpy_int64_becomes_python_int(self):
        import numpy as np
        scores = [np.int64(1), np.int32(2)]
        result = self.engine._convert_scores(scores)
        for s in result:
            assert type(s) is int
