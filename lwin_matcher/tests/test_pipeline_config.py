from __future__ import annotations

from app.service.pipeline.config import LOT_TYPE_FILTERS


def test_lot_type_filters_use_utf8_rose_wine() -> None:
    values = [item["value"] for item in LOT_TYPE_FILTERS]

    assert "Rosé Wine" in values
    assert "Ros茅 Wine" not in values
