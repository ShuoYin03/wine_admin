"""Tests for LwinMatchingParams model validation."""
from __future__ import annotations

import pytest
from app.models.lwin_matching_params import LwinMatchingParams
from app.models.match_result import MatchResult


class TestLwinMatchingParamsVintageValidation:
    def test_integer_vintage_passes_through(self):
        p = LwinMatchingParams(wine_name="Pétrus", vintage=2015)
        assert p.vintage == 2015

    def test_string_digit_vintage_converts_to_int(self):
        p = LwinMatchingParams(wine_name="Pétrus", vintage="2015")
        assert p.vintage == 2015

    def test_nv_vintage_becomes_none(self):
        for val in ("nv", "NV", "n.v.", "non-vintage", ""):
            p = LwinMatchingParams(wine_name="x", vintage=val)
            assert p.vintage is None, f"Expected None for vintage={val!r}"

    def test_none_vintage_stays_none(self):
        p = LwinMatchingParams(wine_name="x", vintage=None)
        assert p.vintage is None

    def test_invalid_string_vintage_becomes_none(self):
        p = LwinMatchingParams(wine_name="x", vintage="unknown")
        assert p.vintage is None


class TestLwinMatchingParamsStringFields:
    def test_none_fields_become_empty_string(self):
        p = LwinMatchingParams(wine_name="x", lot_producer=None, colour=None)
        assert p.lot_producer == ""
        assert p.colour == ""

    def test_numeric_lot_producer_becomes_empty_string(self):
        p = LwinMatchingParams(wine_name="x", lot_producer=42)
        assert p.lot_producer == ""

    def test_wine_name_is_required(self):
        # wine_name cannot be omitted
        with pytest.raises(Exception):
            LwinMatchingParams()

    def test_vintage_defaults_to_none(self):
        p = LwinMatchingParams(wine_name="Opus One")
        assert p.vintage is None

    def test_explicitly_passed_none_becomes_empty_string(self):
        # The ensure_string validator runs when the field is explicitly set to None
        p = LwinMatchingParams(
            wine_name="Opus One",
            lot_producer=None,
            region=None,
            sub_region=None,
            country=None,
            colour=None,
        )
        assert p.lot_producer == ""
        assert p.region == ""
        assert p.sub_region == ""
        assert p.country == ""
        assert p.colour == ""


class TestMatchResult:
    def test_enum_values(self):
        assert MatchResult.EXACT_MATCH.value == "exact_match"
        assert MatchResult.MULTI_MATCH.value == "multi_match"
        assert MatchResult.NOT_MATCH.value == "not_match"
