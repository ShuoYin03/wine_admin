from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.database.models.auction_sales_db import AuctionSalesModel  # noqa: E402
from shared.database.models.auction_db import AuctionModel  # noqa: E402,F401
from shared.database.models.lot_db import LotModel  # noqa: E402
from shared.database.models.lot_item_db import LotItemModel  # noqa: E402
from shared.database.models.lwin_matching_db import LwinMatchingModel  # noqa: E402
from shared.database.session_factory import (  # noqa: E402
    dispose_shared_engine,
    get_shared_session_factory,
)


@dataclass(frozen=True)
class ResetCounts:
    lots: int
    lot_items: int
    lwin_matching: int
    auction_sales: int


@dataclass(frozen=True)
class SpiderSubprocess:
    args: list[str]
    cwd: Path
    env_updates: dict[str, str]


def parse_csv_values(values: Sequence[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for part in value.split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result


def build_spider_subprocess(
    project_root: Path,
    python_executable: str,
    houses: Sequence[str],
    full_fetch: bool = False,
    target_auction_ids: Sequence[str] | None = None,
) -> SpiderSubprocess:
    env_updates = {"FULL_FETCH": "True" if full_fetch else "False"}
    target_auction_ids = list(target_auction_ids or [])
    if target_auction_ids:
        env_updates["BACKFILL_AUCTION_IDS"] = ",".join(target_auction_ids)

    return SpiderSubprocess(
        args=[
            python_executable,
            "-m",
            "wine_spider.run_spiders",
            "--houses",
            ",".join(houses),
        ],
        cwd=project_root / "wine_spider",
        env_updates=env_updates,
    )


def count_reset_rows(session, auction_ids: Sequence[str]) -> ResetCounts:
    lot_ids = select(LotModel.external_id).where(LotModel.auction_id.in_(auction_ids))
    lot_item_ids = select(LotItemModel.id).where(LotItemModel.lot_id.in_(lot_ids))

    return ResetCounts(
        lots=session.scalar(
            select(func.count(LotModel.id)).where(LotModel.auction_id.in_(auction_ids))
        )
        or 0,
        lot_items=session.scalar(
            select(func.count(LotItemModel.id)).where(LotItemModel.lot_id.in_(lot_ids))
        )
        or 0,
        lwin_matching=session.scalar(
            select(func.count(LwinMatchingModel.id)).where(
                LwinMatchingModel.lot_item_id.in_(lot_item_ids)
            )
        )
        or 0,
        auction_sales=session.scalar(
            select(func.count(AuctionSalesModel.id)).where(
                AuctionSalesModel.auction_id.in_(auction_ids)
            )
        )
        or 0,
    )


def reset_partial_auctions(session, auction_ids: Sequence[str]) -> ResetCounts:
    counts = count_reset_rows(session, auction_ids)
    lot_ids = select(LotModel.external_id).where(LotModel.auction_id.in_(auction_ids))
    lot_item_ids = select(LotItemModel.id).where(LotItemModel.lot_id.in_(lot_ids))

    session.query(LwinMatchingModel).filter(
        LwinMatchingModel.lot_item_id.in_(lot_item_ids)
    ).delete(synchronize_session=False)
    session.query(LotItemModel).filter(
        LotItemModel.lot_id.in_(lot_ids)
    ).delete(synchronize_session=False)
    session.query(AuctionSalesModel).filter(
        AuctionSalesModel.auction_id.in_(auction_ids)
    ).delete(synchronize_session=False)
    session.query(LotModel).filter(
        LotModel.auction_id.in_(auction_ids)
    ).delete(synchronize_session=False)

    return counts


def run_spider(command: SpiderSubprocess) -> int:
    env = os.environ.copy()
    env.update(command.env_updates)
    completed = subprocess.run(command.args, cwd=command.cwd, env=env, check=False)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare partial auctions for backfill, then optionally run spiders "
            "with FULL_FETCH=False by default so complete auctions are skipped."
        )
    )
    parser.add_argument(
        "--houses",
        nargs="+",
        required=True,
        help="Auction houses to run, e.g. tajan or tajan,christies.",
    )
    parser.add_argument(
        "--reset-auction-id",
        nargs="*",
        default=[],
        help=(
            "Existing partial auction external_id(s) to clear before backfill. "
            "Comma-separated values are accepted."
        ),
    )
    parser.add_argument(
        "--apply-reset",
        action="store_true",
        help="Actually delete lots/lot_items/lwin_matching/auction_sales for reset auction ids.",
    )
    parser.add_argument(
        "--run-spider",
        action="store_true",
        help="Run selected spiders after the dry-run/reset step.",
    )
    parser.add_argument(
        "--full-fetch",
        action="store_true",
        help="Run selected spiders with FULL_FETCH=True after the dry-run/reset step.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    houses = parse_csv_values(args.houses)
    auction_ids = parse_csv_values(args.reset_auction_id)

    if not houses:
        raise SystemExit("--houses cannot be empty")

    if auction_ids:
        SessionFactory = get_shared_session_factory()
        session = SessionFactory()
        try:
            if args.apply_reset:
                counts = reset_partial_auctions(session, auction_ids)
                session.commit()
                action = "Deleted"
            else:
                counts = count_reset_rows(session, auction_ids)
                session.rollback()
                action = "Dry-run, would delete"
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            dispose_shared_engine()

        print(
            f"{action}: lots={counts.lots}, lot_items={counts.lot_items}, "
            f"lwin_matching={counts.lwin_matching}, auction_sales={counts.auction_sales}"
        )
        if not args.apply_reset:
            print("Add --apply-reset to clear these partial rows.")

    if args.run_spider:
        command = build_spider_subprocess(
            PROJECT_ROOT,
            sys.executable,
            houses,
            full_fetch=args.full_fetch,
            target_auction_ids=auction_ids,
        )
        print(
            f"Running spider with FULL_FETCH={command.env_updates['FULL_FETCH']}: "
            f"{' '.join(command.args)}"
        )
        return run_spider(command)

    if not auction_ids:
        print("No reset auction ids supplied. Use --run-spider to backfill zero-lot auctions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
