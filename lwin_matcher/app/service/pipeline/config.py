from __future__ import annotations

from dataclasses import dataclass

AUCTION_HOUSES: list[str] = [
    "Sotheby's",
    "Christie's",
    "Bonhams",
    "Sylvie's",
    "Wineauctioneer",
    "Baghera",
    "Tajan",
    "Zachys",
    "Steinfels",
]

# Canonical wine lot-type filters (dict format, @> operator for ARRAY columns)
LOT_TYPE_FILTERS: list[dict] = [
    {"field": "lot_type", "op": "@>", "value": "Wine"},
    {"field": "lot_type", "op": "@>", "value": "wine"},
    {"field": "lot_type", "op": "@>", "value": "Wine & Spirits"},
    {"field": "lot_type", "op": "@>", "value": "White Wine"},
    {"field": "lot_type", "op": "@>", "value": "Sweet Wine"},
    {"field": "lot_type", "op": "@>", "value": "W"},
    {"field": "lot_type", "op": "@>", "value": "Sparkling Wine"},
    {"field": "lot_type", "op": "@>", "value": "Red Wine"},
    {"field": "lot_type", "op": "@>", "value": "Rosé Wine"},
    {"field": "lot_type", "op": "@>", "value": "Orange Wine"},
    {"field": "lot_type", "op": "@>", "value": "Fruit Wine"},
    {"field": "lot_type", "op": "@>", "value": "Fortified Wine"},
]


@dataclass
class PipelineConfig:
    auction_house: str | None = None
    worker_count: int = 32
    fetch_batch_size: int = 500
    flush_size: int = 500
    work_queue_maxsize: int = 2000
    resume: bool = True
    # Sample mode (output_csv != None activates sample mode)
    sample_size: int | None = None
    sample_seed: int = 42
    output_csv: str | None = None
