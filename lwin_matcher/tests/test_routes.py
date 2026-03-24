"""Tests for Flask route handlers using the test client.

All database clients and the matching engine are replaced with mocks
so these tests run without a real database or BM25 index.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.models.match_result import MatchResult


# ── App factory with mocked dependencies ─────────────────────────────────────

def make_test_app():
    """Create a Flask test app with all DB/engine dependencies mocked."""
    from flask import Flask
    from app.routes.match import match_blueprint
    from app.routes.lwin_query import lwin_query_blueprint

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    # Inject mock clients directly onto the app
    app.lwin_matching_engine = MagicMock()
    app.lwin_database_client = MagicMock()
    app.lwin_matching_client = MagicMock()
    app.lots_client = MagicMock()
    app.auctions_client = MagicMock()
    app.lot_items_client = MagicMock()
    app.auction_sales_client = MagicMock()
    app.fx_rates_client = MagicMock()

    app.register_blueprint(match_blueprint)
    app.register_blueprint(lwin_query_blueprint)

    return app


@pytest.fixture
def client():
    app = make_test_app()
    with app.test_client() as c:
        with app.app_context():
            yield c, app


# ── /match route ─────────────────────────────────────────────────────────────

class TestMatchRoute:
    def test_match_returns_200_on_success(self, client):
        c, app = client
        import pandas as pd
        from collections import OrderedDict

        app.lwin_matching_engine.match.return_value = (
            MatchResult.EXACT_MATCH,
            [1000001],
            [0.95],
            [OrderedDict([
                ("id", 1), ("lwin", 1000001), ("display_name", "Chateau Petrus"),
                ("reference", None), ("date_added", pd.Timestamp("2020-01-01")),
                ("date_updated", pd.Timestamp("2020-01-01")),
            ])],
        )

        payload = {
            "wine_name": "Chateau Petrus",
            "lot_producer": "Petrus",
            "vintage": "2015",
            "region": "Bordeaux",
            "country": "France",
            "colour": "Red",
        }
        resp = c.post("/match", json=payload)
        assert resp.status_code == 200

    def test_match_response_has_required_keys(self, client):
        c, app = client
        import pandas as pd
        from collections import OrderedDict

        app.lwin_matching_engine.match.return_value = (
            MatchResult.EXACT_MATCH,
            [1000001],
            [0.95],
            [OrderedDict([
                ("id", 1), ("lwin", 1000001), ("display_name", "Chateau Petrus"),
                ("reference", None), ("date_added", pd.Timestamp("2020-01-01")),
                ("date_updated", pd.Timestamp("2020-01-01")),
            ])],
        )

        resp = c.post("/match", json={"wine_name": "Petrus", "lot_producer": "Petrus"})
        data = json.loads(resp.data)
        assert "matched" in data
        assert "lwin_code" in data
        assert "match_score" in data
        assert "match_item" in data

    def test_match_not_match_result(self, client):
        c, app = client
        app.lwin_matching_engine.match.return_value = (
            MatchResult.NOT_MATCH, [], [], []
        )
        resp = c.post("/match", json={"wine_name": "Unknown", "lot_producer": ""})
        data = json.loads(resp.data)
        assert data["matched"] == "not_match"

    def test_match_engine_exception_returns_400(self, client):
        c, app = client
        app.lwin_matching_engine.match.side_effect = RuntimeError("engine error")
        resp = c.post("/match", json={"wine_name": "x", "lot_producer": "y"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_match_lwin_11_code_generated_for_4digit_vintage(self, client):
        c, app = client
        import pandas as pd
        from collections import OrderedDict

        app.lwin_matching_engine.match.return_value = (
            MatchResult.EXACT_MATCH,
            [1000001],
            [0.95],
            [OrderedDict([
                ("id", 1), ("lwin", 1000001), ("display_name", "Chateau Petrus"),
                ("reference", None), ("date_added", pd.Timestamp("2020-01-01")),
                ("date_updated", pd.Timestamp("2020-01-01")),
            ])],
        )

        resp = c.post("/match", json={"wine_name": "Petrus", "lot_producer": "Petrus", "vintage": "2015"})
        data = json.loads(resp.data)
        assert data["lwin_11_code"] == [10000012015]

    def test_match_lwin_11_code_none_for_nv(self, client):
        c, app = client
        import pandas as pd
        from collections import OrderedDict

        app.lwin_matching_engine.match.return_value = (
            MatchResult.EXACT_MATCH,
            [1000001],
            [0.95],
            [OrderedDict([
                ("id", 1), ("lwin", 1000001), ("display_name", "Chateau Petrus"),
                ("reference", None), ("date_added", pd.Timestamp("2020-01-01")),
                ("date_updated", pd.Timestamp("2020-01-01")),
            ])],
        )

        resp = c.post("/match", json={"wine_name": "Petrus", "lot_producer": "Petrus", "vintage": "nv"})
        data = json.loads(resp.data)
        assert data["lwin_11_code"] is None


# ── /match_target route ───────────────────────────────────────────────────────

class TestMatchTargetRoute:
    def test_missing_target_name_returns_400(self, client):
        c, app = client
        resp = c.post("/match_target", json={"wine_name": "Petrus"})
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_not_found_target_returns_400(self, client):
        c, app = client
        app.lwin_database_client.get_by_display_name.return_value = []
        resp = c.post("/match_target", json={"wine_name": "Petrus", "target_name": "Unknown Wine"})
        assert resp.status_code == 400

    def test_multiple_candidates_returns_400(self, client):
        c, app = client
        app.lwin_database_client.get_by_display_name.return_value = [
            {"id": 1}, {"id": 2}
        ]
        resp = c.post("/match_target", json={"wine_name": "Petrus", "target_name": "Duplicate"})
        assert resp.status_code == 400

    def test_successful_match_target(self, client):
        c, app = client
        app.lwin_database_client.get_by_display_name.return_value = [{"id": 42}]
        app.lwin_matching_engine.match_target_by_id.return_value = 0.87
        resp = c.post("/match_target", json={"wine_name": "Petrus", "target_name": "Chateau Petrus"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "match_score" in data
        assert data["match_score"] == pytest.approx(0.87)
        assert data["target_idx"] == 42


# ── /lwin_query route ─────────────────────────────────────────────────────────

class TestLwinQueryRoute:
    def test_returns_data_list(self, client):
        c, app = client
        app.lwin_matching_client.query_lwin_with_lots.return_value = (
            [{"id": 1, "display_name": "Petrus"}],
            None,
        )
        resp = c.post("/lwin_query", json={"page": 1, "page_size": 10})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "data" in data

    def test_returns_count_when_requested(self, client):
        c, app = client
        app.lwin_matching_client.query_lwin_with_lots.return_value = (
            [{"id": 1}],
            42,
        )
        resp = c.post("/lwin_query", json={"return_count": True})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "count" in data
        assert data["count"] == 42

    def test_exception_returns_500(self, client):
        c, app = client
        app.lwin_matching_client.query_lwin_with_lots.side_effect = RuntimeError("db error")
        resp = c.post("/lwin_query", json={})
        assert resp.status_code == 500

    def test_lwin_query_count_route(self, client):
        c, app = client
        app.lwin_matching_client.query_exact_match_count.return_value = 100
        app.lwin_matching_client.query_multi_match_count.return_value = 20
        app.lwin_matching_client.query_not_match_count.return_value = 5
        resp = c.get("/lwin_query_count")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["data"]["exact_match_count"] == 100
        assert data["data"]["multi_match_count"] == 20
        assert data["data"]["not_match_count"] == 5


