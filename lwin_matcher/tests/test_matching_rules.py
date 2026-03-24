"""Unit tests for all matching rule specifications.

All rules are pure logic — no database, no BM25, no external I/O.
Each test builds a MatchingContext from a plain dict (row) + LwinMatchingParams.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.models.lwin_matching_params import LwinMatchingParams
from app.models.match_result import MatchResult
from app.service.matching_rules.matching_context import MatchingContext
from app.service.matching_rules.bordeaux_rule import BordeauxRule
from app.service.matching_rules.burgundy_rule import BurgundyRule
from app.service.matching_rules.colour_should_match_rule import ColourShouldMatchRule
from app.service.matching_rules.not_assortment_case_rule import NotAssortmentCaseRule
from app.service.matching_rules.mixed_lots_should_not_match_rule import MixedLotsShouldNotMatchRule
from app.service.matching_rules.miss_producer_should_not_match_rule import MissProducerShouldNotMatchRule
from app.service.matching_rules.fuzzy_score_should_above_threshold_rule import FuzzyScoreShouldAboveThresholdRule
from app.service.matching_rules.wine_category_should_exist_in_name_rule import WineCategoryShouldExistInNameRule
from app.service.matching_rules.site_should_exist_in_name_rule import SiteShouldExistInNameRule
from app.service.matching_rules.and_specification import AndSpecification
from app.service.matching_rules.or_specification import OrSpecification
from app.service.matching_rules.not_specification import NotSpecification


def make_ctx(row: dict, **params_kwargs) -> MatchingContext:
    params = LwinMatchingParams(wine_name=params_kwargs.pop("wine_name", "test wine"), **params_kwargs)
    row_series = pd.Series(row)
    return MatchingContext(row=row_series, params=params)


# ─── ColourShouldMatchRule ──────────────────────────────────────────────────

class TestColourShouldMatchRule:
    rule = ColourShouldMatchRule()

    def test_red_matches_red(self):
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour="Red")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_white_matches_white(self):
        ctx = make_ctx({"colour": "White"}, wine_name="x", colour="White")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_red_does_not_match_white(self):
        ctx = make_ctx({"colour": "White"}, wine_name="x", colour="Red")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_white_does_not_match_red(self):
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour="White")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_no_colour_param_passes(self):
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour=None)
        assert self.rule.is_satisfied_by(ctx) is True

    def test_no_row_colour_passes(self):
        ctx = make_ctx({"colour": None}, wine_name="x", colour="Red")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_rosé_colour_passes(self):
        # Non-red/white colours are not filtered
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour="Rosé")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_float_colour_passes(self):
        # Handles legacy data where colour is a float (NaN)
        params = LwinMatchingParams(wine_name="x")
        params.colour = 1.0  # bypass validator
        row = pd.Series({"colour": "Red"})
        ctx = MatchingContext(row=row, params=params)
        assert self.rule.is_satisfied_by(ctx) is True


# ─── NotAssortmentCaseRule ──────────────────────────────────────────────────

class TestNotAssortmentCaseRule:
    rule = NotAssortmentCaseRule()

    def test_normal_wine_passes(self):
        ctx = make_ctx({"display_name": "Pétrus", "wine": "Pétrus"}, wine_name="x")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_assortment_in_display_name_fails(self):
        ctx = make_ctx({"display_name": "Assortment of Bordeaux", "wine": ""}, wine_name="x")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_assortment_in_wine_fails(self):
        ctx = make_ctx({"display_name": "Normal", "wine": "Assortment Case"}, wine_name="x")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_assortment_case_insensitive(self):
        ctx = make_ctx({"display_name": "ASSORTMENT", "wine": ""}, wine_name="x")
        assert self.rule.is_satisfied_by(ctx) is False


# ─── MixedLotsShouldNotMatchRule ───────────────────────────────────────────

class TestMixedLotsShouldNotMatchRule:
    rule = MixedLotsShouldNotMatchRule()

    def test_normal_lot_passes(self):
        ctx = make_ctx({}, wine_name="Château Pétrus 2015", lot_producer="Pétrus")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_mixed_in_wine_name_fails(self):
        ctx = make_ctx({}, wine_name="Mixed Case of Bordeaux")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_assortment_in_wine_name_fails(self):
        ctx = make_ctx({}, wine_name="Assortment of Burgundy Premiers Crus")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_vertical_in_wine_name_fails(self):
        ctx = make_ctx({}, wine_name="Petrus Vertical Tasting")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_mixed_in_producer_fails(self):
        ctx = make_ctx({}, wine_name="Bordeaux", lot_producer="Mixed Producers")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_long_name_with_multiple_brackets_fails(self):
        long_name = "A" * 151 + " (item1) (item2)"
        ctx = make_ctx({}, wine_name=long_name)
        assert self.rule.is_satisfied_by(ctx) is False

    def test_long_name_single_bracket_passes(self):
        long_name = "A" * 151 + " (single)"
        ctx = make_ctx({}, wine_name=long_name)
        assert self.rule.is_satisfied_by(ctx) is True


# ─── MissProducerShouldNotMatchRule ────────────────────────────────────────

class TestMissProducerShouldNotMatchRule:
    rule = MissProducerShouldNotMatchRule()

    def test_producer_present_passes(self):
        ctx = make_ctx({}, wine_name="x", lot_producer="Château Pétrus")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_empty_producer_fails(self):
        ctx = make_ctx({}, wine_name="x", lot_producer="")
        assert self.rule.is_satisfied_by(ctx) is False

    def test_none_producer_fails(self):
        ctx = make_ctx({}, wine_name="x", lot_producer=None)
        assert self.rule.is_satisfied_by(ctx) is False

    def test_whitespace_only_producer_fails(self):
        ctx = make_ctx({}, wine_name="x", lot_producer="   ")
        assert self.rule.is_satisfied_by(ctx) is False


# ─── BordeauxRule ──────────────────────────────────────────────────────────

class TestBordeauxRule:
    rule = BordeauxRule()

    def test_non_bordeaux_region_always_passes(self):
        ctx = make_ctx(
            {"producer_name": "Domaine de la Romanée-Conti"},
            wine_name="La Tâche",
            region="Burgundy",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_bordeaux_producer_matches_wine_name(self):
        # Producer name ≈ wine name → passes
        ctx = make_ctx(
            {"producer_name": "Chateau Petrus"},
            wine_name="Chateau Petrus",
            region="Bordeaux",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_bordeaux_producer_within_wine_name_passes(self):
        ctx = make_ctx(
            {"producer_name": "Petrus"},
            wine_name="Chateau Petrus 2015",
            region="Bordeaux",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_bordeaux_unrelated_producer_fails(self):
        ctx = make_ctx(
            {"producer_name": "Chateau Margaux"},
            wine_name="Pichon Baron",
            region="Bordeaux",
        )
        assert self.rule.is_satisfied_by(ctx) is False

    def test_bordeaux_close_edit_distance_passes(self):
        # "Latour" vs "La tour" — edit distance ≤ 2
        ctx = make_ctx(
            {"producer_name": "latour"},
            wine_name="la tour",
            region="Bordeaux",
        )
        assert self.rule.is_satisfied_by(ctx) is True


# ─── BurgundyRule ──────────────────────────────────────────────────────────

class TestBurgundyRule:
    rule = BurgundyRule()

    def test_non_burgundy_always_passes(self):
        ctx = make_ctx(
            {"producer_name": "Pétrus", "producer_title": "", "sub_region": "Pomerol"},
            wine_name="Pétrus",
            region="Bordeaux",
            country="France",
            sub_region="Pomerol",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_burgundy_producer_in_name_passes(self):
        ctx = make_ctx(
            {
                "producer_name": "romanee conti",
                "producer_title": "domaine de la",
                "sub_region": "Vosne-Romanée",
            },
            wine_name="Domaine de la Romanee Conti La Tache",
            region="Burgundy",
            lot_producer="Domaine de la Romanee Conti",
            sub_region="Vosne-Romanée",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_burgundy_wrong_sub_region_fails(self):
        ctx = make_ctx(
            {
                "producer_name": "leroy",
                "producer_title": "domaine",
                "sub_region": "Gevrey-Chambertin",
            },
            wine_name="Domaine Leroy Chambolle Musigny",
            region="Burgundy",
            lot_producer="Domaine Leroy",
            sub_region="Chambolle-Musigny",
        )
        assert self.rule.is_satisfied_by(ctx) is False

    def test_burgundy_wrong_producer_with_title_fails(self):
        # producer_name "leroy" not in wine name, producer_title "maison" not in wine name,
        # and lot_producer "Domaine Dujac" doesn't match row producer — should fail.
        ctx = make_ctx(
            {
                "producer_name": "leroy",
                "producer_title": "maison",  # not in "domaine dujac chambolle musigny"
                "sub_region": "",
            },
            wine_name="Domaine Dujac Chambolle Musigny",
            region="Burgundy",
            lot_producer="Domaine Dujac",
            sub_region="",
        )
        assert self.rule.is_satisfied_by(ctx) is False


# ─── FuzzyScoreShouldAboveThresholdRule ────────────────────────────────────

class TestFuzzyScoreShouldAboveThresholdRule:
    rule = FuzzyScoreShouldAboveThresholdRule()

    def test_matching_fields_pass(self):
        ctx = make_ctx(
            {"producer_name": "Petrus", "country": "France", "region": "Bordeaux", "sub_region": "Pomerol"},
            wine_name="x",
            lot_producer="Petrus",
            country="France",
            region="Bordeaux",
            sub_region="Pomerol",
        )
        assert self.rule.is_satisfied_by(ctx) is True

    def test_mismatched_country_fails(self):
        ctx = make_ctx(
            {"producer_name": "Petrus", "country": "Italy", "region": "Bordeaux", "sub_region": ""},
            wine_name="x",
            lot_producer="Petrus",
            country="France",
        )
        assert self.rule.is_satisfied_by(ctx) is False

    def test_empty_params_pass(self):
        ctx = make_ctx(
            {"producer_name": "Petrus", "country": "France", "region": "Bordeaux", "sub_region": ""},
            wine_name="x",
        )
        assert self.rule.is_satisfied_by(ctx) is True


# ─── WineCategoryShouldExistInNameRule ─────────────────────────────────────

class TestWineCategoryShouldExistInNameRule:
    rule = WineCategoryShouldExistInNameRule()

    def test_no_row_wine_passes(self):
        ctx = make_ctx({"wine": None}, wine_name="Petrus")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_matching_wine_category_passes(self):
        ctx = make_ctx({"wine": "Petrus"}, wine_name="Petrus 2015")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_unrelated_wine_category_fails(self):
        ctx = make_ctx({"wine": "La Tache"}, wine_name="Petrus 2015")
        assert self.rule.is_satisfied_by(ctx) is False


# ─── SiteShouldExistInNameRule ─────────────────────────────────────────────

class TestSiteShouldExistInNameRule:
    rule = SiteShouldExistInNameRule()

    def test_no_site_passes(self):
        ctx = make_ctx({"site": None}, wine_name="Petrus")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_matching_site_passes(self):
        ctx = make_ctx({"site": "Petrus"}, wine_name="Chateau Petrus 2015")
        assert self.rule.is_satisfied_by(ctx) is True

    def test_unrelated_site_fails(self):
        ctx = make_ctx({"site": "Mouton"}, wine_name="Petrus 2015")
        assert self.rule.is_satisfied_by(ctx) is False


# ─── Composite Specifications ──────────────────────────────────────────────

class TestCompositeSpecifications:
    def test_and_both_pass(self):
        colour_rule = ColourShouldMatchRule()
        miss_rule = MissProducerShouldNotMatchRule()
        combined = colour_rule & miss_rule
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour="Red", lot_producer="Petrus")
        assert combined.is_satisfied_by(ctx) is True

    def test_and_one_fails(self):
        colour_rule = ColourShouldMatchRule()
        miss_rule = MissProducerShouldNotMatchRule()
        combined = colour_rule & miss_rule
        # colour matches but no producer
        ctx = make_ctx({"colour": "Red"}, wine_name="x", colour="Red", lot_producer="")
        assert combined.is_satisfied_by(ctx) is False

    def test_or_one_passes(self):
        # colour mismatch, but producer present (miss_rule passes)
        colour_rule = ColourShouldMatchRule()
        miss_rule = MissProducerShouldNotMatchRule()
        combined = colour_rule | miss_rule
        ctx = make_ctx({"colour": "White"}, wine_name="x", colour="Red", lot_producer="Petrus")
        assert combined.is_satisfied_by(ctx) is True

    def test_not_inverts(self):
        miss_rule = MissProducerShouldNotMatchRule()
        inverted = ~miss_rule
        # producer present → miss_rule passes → inverted fails
        ctx = make_ctx({}, wine_name="x", lot_producer="Petrus")
        assert inverted.is_satisfied_by(ctx) is False
        # no producer → miss_rule fails → inverted passes
        ctx2 = make_ctx({}, wine_name="x", lot_producer="")
        assert inverted.is_satisfied_by(ctx2) is True

    def test_operator_sugar_equals_explicit_class(self):
        a = ColourShouldMatchRule()
        b = MissProducerShouldNotMatchRule()
        assert isinstance(a & b, AndSpecification)
        assert isinstance(a | b, OrSpecification)
        assert isinstance(~a, NotSpecification)
