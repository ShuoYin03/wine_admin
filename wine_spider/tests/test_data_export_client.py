from __future__ import annotations

import unittest
from contextlib import contextmanager

from shared.database.data_export_client import DataExportClient, format_export_array


class FakeQuery:
    def __init__(self):
        self.outerjoin_clauses = []

    def join(self, *_args, **_kwargs):
        return self

    def outerjoin(self, _model, onclause):
        self.outerjoin_clauses.append(str(onclause))
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return []


class FakeSession:
    def __init__(self):
        self.query_obj = FakeQuery()

    def query(self, *_models):
        return self.query_obj


class DataExportClientTests(unittest.TestCase):
    def test_lot_export_joins_lwin_matching_by_lot_item_id(self):
        client = DataExportClient()
        fake_session = FakeSession()

        @contextmanager
        def fake_session_scope():
            yield fake_session

        client.session_scope = fake_session_scope

        client.export_lots_with_items_by_house("Sotheby's")

        self.assertTrue(
            any("lwin_matching.lot_item_id" in clause for clause in fake_session.query_obj.outerjoin_clauses),
            fake_session.query_obj.outerjoin_clauses,
        )

    def test_format_export_array_restores_character_arrays(self):
        self.assertEqual(format_export_array(["W", "i", "n", "e", " ", "&", " ", "S", "p", "i", "r", "i", "t", "s"]), "Wine & Spirits")

    def test_format_export_array_joins_normal_arrays(self):
        self.assertEqual(format_export_array(["Wine", "Spirits"]), "Wine; Spirits")


if __name__ == "__main__":
    unittest.main()
