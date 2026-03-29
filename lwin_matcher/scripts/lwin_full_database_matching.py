"""
lwin_full_database_matching.py -- CLI entry point for LWIN Matching.

Modes:
    full    Run the full Producer-Consumer pipeline, optionally filtered to one
            auction house. Supports checkpoint/resume.
    sample  Fetch a random sample of lots, run matching, and export results to CSV
            (useful for quality checks without writing to DB).

Usage examples:
    python scripts/lwin_full_database_matching.py                          # full, all houses
    python scripts/lwin_full_database_matching.py --auction-house Zachys   # single house
    python scripts/lwin_full_database_matching.py --no-resume              # restart from 0
    python scripts/lwin_full_database_matching.py --mode sample --sample-size 50
"""

from __future__ import annotations

import os
import sys

# --- path bootstrap (script lives in lwin_matcher/scripts/) ---
_here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_here, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(_here, "..", "..")))

import argparse
from dotenv import load_dotenv

load_dotenv()

from app.service.lwin_matching_engine import LwinMatcherEngine
from shared.database.lwin_database_client import LwinDatabaseClient
from app.service.pipeline import (
    AUCTION_HOUSES,
    LwinMatchingPipeline,
    PipelineConfig,
)
from shared.database.lwin_matching_client import LwinMatchingClient
from shared.database.lots_client import LotsClient


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _build_arg_parser():
    parser = argparse.ArgumentParser(description="LWIN database matching")
    parser.add_argument(
        "--mode", choices=["full", "sample"], default="full",
        help="full: run pipeline to DB; sample: random N lots to CSV only",
    )
    parser.add_argument(
        "--auction-house",
        choices=AUCTION_HOUSES + ["all"],
        default="all",
        dest="auction_house",
        help="Restrict to a single auction house (default: all)",
    )
    parser.add_argument(
        "--no-resume", action="store_false", dest="resume",
        help="Ignore existing checkpoint and restart from offset 0",
    )
    parser.add_argument("--workers", type=int, default=32, help="Worker thread count")
    parser.add_argument("--batch-size", type=int, default=500, dest="batch_size")
    parser.add_argument("--sample-size", type=int, default=100, dest="sample_size")
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(os.getcwd(), "sample_matches.csv"),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()

    auction_house: str | None = None if args.auction_house == "all" else args.auction_house

    lwin_db_client = LwinDatabaseClient()
    lots_client = LotsClient()
    lwin_client = LwinMatchingClient()
    engine = LwinMatcherEngine(lwin_db_client.get_all())

    config = PipelineConfig(
        auction_house=auction_house,
        worker_count=args.workers,
        fetch_batch_size=args.batch_size,
        resume=args.resume,
        sample_size=args.sample_size if args.mode == "sample" else None,
        sample_seed=args.seed,
        output_csv=args.output if args.mode == "sample" else None,
    )
    pipeline = LwinMatchingPipeline(
        config=config,
        engine=engine,
        lots_client=lots_client,
        lwin_client=lwin_client,
    )
    pipeline.run()
