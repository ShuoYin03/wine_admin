
from __future__ import annotations

import argparse
import json
import os
import re
import runpy
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WINE_SPIDER_ROOT = REPO_ROOT / "wine_spider"

MODULE_REPORTS = [
    ("Baghera", "wine_spider.spiders.reports.generate_baghera_report", 240),
    ("Bonhams", "wine_spider.spiders.reports.generate_bonhams_report", 240),
    ("Christie's", "wine_spider.spiders.reports.generate_christies_report", 900),
    ("Sotheby's", "wine_spider.spiders.reports.generate_sothebys_report", 600),
    ("Steinfels", "wine_spider.spiders.reports.generate_steinfels_report", 240),
    ("Sylvie's", "wine_spider.spiders.reports.generate_sylvies_report", 240),
    ("Tajan", "wine_spider.spiders.reports.generate_tajan_report", 900),
    ("Wineauctioneer", "wine_spider.spiders.reports.generate_wineauctioneer_report", 240),
]

ZACHYS_REPORT = ("Zachys", "zachys_report_spider", 600)


def configure_paths() -> None:
    for path in (REPO_ROOT, WINE_SPIDER_ROOT):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def preload_models() -> None:
    import shared.database.models.auction_sales_db  # noqa: F401
    import shared.database.models.lot_item_db  # noqa: F401
    import shared.database.models.lwin_matching_db  # noqa: F401


def child_env(output_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [
        str(REPO_ROOT),
        str(WINE_SPIDER_ROOT),
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = os.pathsep.join(part for part in pythonpath_parts if part)
    env["PYTHONIOENCODING"] = "utf-8"
    env["REPORT_OUT"] = str(output_dir)
    return env


def run_child(mode: str, output_dir: Path, module: str | None, timeout: int) -> dict:
    command = [sys.executable, __file__, mode, "--output-dir", str(output_dir)]
    if module:
        command.extend(["--module", module])

    start = time.time()
    try:
        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env=child_env(output_dir),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "returncode": result.returncode,
            "elapsed_seconds": round(time.time() - start, 2),
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else str(exc.stdout or "")
        stderr = exc.stderr if isinstance(exc.stderr, str) else str(exc.stderr or "")
        return {
            "returncode": "timeout",
            "elapsed_seconds": round(time.time() - start, 2),
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
        }


def run_module(module: str, output_dir: Path) -> None:
    configure_paths()
    preload_models()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(output_dir)
    runpy.run_module(module, run_name="__main__")


def run_zachys(output_dir: Path) -> None:
    configure_paths()
    preload_models()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(output_dir)

    from wine_spider.spiders.reports.generate_zachys_report import run_report

    run_report()


def normalize_house_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def parse_house_values(values: list[str] | None) -> list[str]:
    parsed: list[str] = []
    for value in values or []:
        for part in value.split(","):
            part = part.strip()
            if part:
                parsed.append(part)
    return parsed


def resolve_house_values(
    arg_values: list[str] | None,
    environ: dict[str, str] | None = None,
) -> list[str]:
    values = parse_house_values(arg_values)
    if values:
        return values

    environ = environ or os.environ
    npm_houses = environ.get("npm_config_houses", "").strip()
    if npm_houses:
        return parse_house_values([npm_houses])

    return ["all"]


def resolve_output_dir(arg_value: str | None, environ: dict[str, str] | None = None) -> Path:
    if arg_value:
        return Path(arg_value).resolve()

    environ = environ or os.environ
    npm_output_dir = environ.get("npm_config_output_dir", "").strip()
    if npm_output_dir:
        return Path(npm_output_dir).resolve()

    return default_output_dir()


def env_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_include_zachys(arg_value: bool, environ: dict[str, str] | None = None) -> bool:
    if arg_value:
        return True

    environ = environ or os.environ
    return env_truthy(environ.get("npm_config_include_zachys", ""))


def resolve_report_selection(
    houses: list[str] | None,
    include_zachys: bool = False,
) -> tuple[list[tuple[str, str, int]], bool]:
    requested = parse_house_values(houses)
    if not requested or any(normalize_house_name(house) == "all" for house in requested):
        return MODULE_REPORTS, True

    reports_by_house = {
        normalize_house_name(house): (house, module, timeout)
        for house, module, timeout in MODULE_REPORTS
    }
    reports_by_house["zachys"] = ZACHYS_REPORT

    selected_reports: list[tuple[str, str, int]] = []
    selected_zachys = include_zachys
    unknown_houses: list[str] = []
    seen: set[str] = set()

    for house in requested:
        key = normalize_house_name(house)
        report = reports_by_house.get(key)
        if report is None:
            unknown_houses.append(house)
            continue
        if key in seen:
            continue
        seen.add(key)
        if key == "zachys":
            selected_zachys = True
            continue
        selected_reports.append(report)

    if unknown_houses:
        valid = ", ".join(
            [house for house, _, _ in MODULE_REPORTS] + [ZACHYS_REPORT[0], "all"]
        )
        raise SystemExit(
            f"Unknown house(s): {', '.join(unknown_houses)}. Valid values: {valid}"
        )

    return selected_reports, selected_zachys


def default_output_dir() -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "exports" / f"scraping_reports_{timestamp}"


def run_reports(
    output_dir: Path,
    reports: list[tuple[str, str, int]],
    include_zachys: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    statuses = []

    for house, module, timeout in reports:
        print(f"RUN_START\t{house}\t{module}\ttimeout={timeout}s", flush=True)
        status = run_child("_run_module", output_dir, module, timeout)
        status.update({"house": house, "module": module})
        statuses.append(status)
        print(
            f"RUN_DONE\t{house}\treturncode={status['returncode']}"
            f"\telapsed={status['elapsed_seconds']}s",
            flush=True,
        )
        if status["stdout_tail"].strip():
            print("STDOUT_TAIL_BEGIN")
            print(status["stdout_tail"][-1200:])
            print("STDOUT_TAIL_END")
        if status["stderr_tail"].strip():
            print("STDERR_TAIL_BEGIN")
            print(status["stderr_tail"][-1200:])
            print("STDERR_TAIL_END")

    if include_zachys:
        house, module, timeout = ZACHYS_REPORT
        print(f"RUN_START\t{house}\t{module}\ttimeout={timeout}s", flush=True)
        status = run_child("_run_zachys", output_dir, None, timeout)
        status.update({"house": house, "module": module})
        statuses.append(status)
        print(
            f"RUN_DONE\t{house}\treturncode={status['returncode']}"
            f"\telapsed={status['elapsed_seconds']}s",
            flush=True,
        )
        if status["stdout_tail"].strip():
            print("STDOUT_TAIL_BEGIN")
            print(status["stdout_tail"][-1200:])
            print("STDOUT_TAIL_END")
        if status["stderr_tail"].strip():
            print("STDERR_TAIL_BEGIN")
            print(status["stderr_tail"][-1200:])
            print("STDERR_TAIL_END")

    (output_dir / "runner_status.json").write_text(
        json.dumps(statuses, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"REPORT_OUT\t{output_dir}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default="run_all")
    parser.add_argument(
        "--houses",
        nargs="*",
        default=[],
        help="Auction house(s) to report, e.g. all, wineauctioneer, or bonhams,tajan.",
    )
    parser.add_argument("--output-dir")
    parser.add_argument("--module")
    parser.add_argument("--include-zachys", action="store_true")
    return parser.parse_args()


def main() -> None:
    configure_stdio()
    args = parse_args()
    output_dir = resolve_output_dir(args.output_dir)

    if args.mode == "_run_module":
        if not args.module:
            raise SystemExit("--module is required for _run_module")
        run_module(args.module, output_dir)
        return

    if args.mode == "_run_zachys":
        run_zachys(output_dir)
        return

    houses = resolve_house_values(args.houses)
    include_zachys_arg = resolve_include_zachys(args.include_zachys)
    reports, include_zachys = resolve_report_selection(houses, include_zachys_arg)
    run_reports(output_dir, reports, include_zachys=include_zachys)


if __name__ == "__main__":
    main()
