import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "backfill_incomplete_auctions.py"
)

spec = importlib.util.spec_from_file_location("backfill_incomplete_auctions", SCRIPT_PATH)
backfill_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = backfill_module
spec.loader.exec_module(backfill_module)

build_spider_subprocess = backfill_module.build_spider_subprocess
parse_csv_values = backfill_module.parse_csv_values


def test_parse_csv_values_accepts_commas_and_repeated_args():
    assert parse_csv_values(["tajan, christies", "sothebys"]) == [
        "tajan",
        "christies",
        "sothebys",
    ]


def test_build_spider_subprocess_forces_incremental_fetch():
    command = build_spider_subprocess(
        project_root=Path("E:/repo"),
        python_executable="python",
        houses=["tajan"],
    )

    assert command.args == [
        "python",
        "-m",
        "wine_spider.run_spiders",
        "--houses",
        "tajan",
    ]
    assert command.cwd == Path("E:/repo/wine_spider")
    assert command.env_updates == {"FULL_FETCH": "False"}


def test_build_spider_subprocess_can_force_full_fetch():
    command = build_spider_subprocess(
        project_root=Path("E:/repo"),
        python_executable="python",
        houses=["sothebys"],
        full_fetch=True,
        target_auction_ids=["auction-1", "auction-2"],
    )

    assert command.env_updates == {
        "FULL_FETCH": "True",
        "BACKFILL_AUCTION_IDS": "auction-1,auction-2",
    }
