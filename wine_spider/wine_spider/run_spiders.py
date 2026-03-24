from __future__ import annotations

import argparse
import os
import re

from scrapy.crawler import CrawlerProcess, AsyncCrawlerProcess
from scrapy.utils.project import get_project_settings

from wine_spider.spiders.baghera import BagheraSpider
from wine_spider.spiders.bonhams import BonhamsSpider
from wine_spider.spiders.christies import ChristiesSpider
from wine_spider.spiders.sothebys import SothebysSpider
from wine_spider.spiders.steinfels import SteinfelsSpider
from wine_spider.spiders.sylvies import SylviesSpider
from wine_spider.spiders.zachys import ZachysSpider
from wine_spider.spiders.tajan import TajanSpider
from wine_spider.spiders.wineauctioneer import WineAuctioneerSpider

SPIDER_REGISTRY: dict[str, type] = {
	"baghera": BagheraSpider,
	"bonhams": BonhamsSpider,
	"christies": ChristiesSpider,
	"sothebys": SothebysSpider,
	"steinfels": SteinfelsSpider,
	"sylvies": SylviesSpider,
	"zachys": ZachysSpider,
	"tajan": TajanSpider,
	"wineauctioneer": WineAuctioneerSpider,
}

# Spiders that use scrapy-playwright and require AsyncCrawlerProcess
PLAYWRIGHT_SPIDERS: frozenset[str] = frozenset({"sothebys", "zachys", "tajan", "wineauctioneer"})

HOUSE_ALIASES: dict[str, str] = {
	"baghera": "baghera",
	"bagheraspider": "baghera",
	"bonhams": "bonhams",
	"bonhamsspider": "bonhams",
	"christies": "christies",
	"christie": "christies",
	"christiesspider": "christies",
	"sothebys": "sothebys",
	"sotheby": "sothebys",
	"sothebysspider": "sothebys",
	"steinfels": "steinfels",
	"steinfelsspider": "steinfels",
	"sylvies": "sylvies",
	"sylviesspider": "sylvies",
	"zachys": "zachys",
	"zachysspider": "zachys",
	"tajan": "tajan",
	"tajanspider": "tajan",
	"wineauctioneer": "wineauctioneer",
	"wineauctioneerspider": "wineauctioneer",
	"all": "all",
}


def _normalize_token(value: str) -> str:
	return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _expand_csv_values(raw_values: list[str]) -> list[str]:
	tokens: list[str] = []
	for raw in raw_values:
		for chunk in raw.split(","):
			candidate = chunk.strip()
			if candidate:
				tokens.append(candidate)
	return tokens


def _resolve_houses(raw_values: list[str], argument_name: str) -> set[str]:
	resolved: set[str] = set()
	invalid: list[str] = []

	for token in _expand_csv_values(raw_values):
		normalized = _normalize_token(token)
		canonical = HOUSE_ALIASES.get(normalized)
		if canonical is None:
			invalid.append(token)
			continue
		resolved.add(canonical)

	if invalid:
		allowed = ", ".join(sorted(SPIDER_REGISTRY.keys()))
		invalid_values = ", ".join(invalid)
		raise ValueError(
			f"Invalid value(s) for {argument_name}: {invalid_values}. "
			f"Allowed values: {allowed}, all"
		)

	return resolved


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Run selected wine auction spiders.",
		epilog=(
			"Examples:\n"
			"  npm run spider --houses=all\n"
			"  npm run spider --houses=zachys,tajan\n"
			"  npm run spider --houses=all --skip=zachys\n"
			"  python -m wine_spider.run_spiders --houses all --skip zachys\n\n"
			f"Available houses: {', '.join(sorted(SPIDER_REGISTRY.keys()))}"
		),
		formatter_class=argparse.RawTextHelpFormatter,
	)
	parser.add_argument(
		"-H",
		"--houses",
		nargs="+",
		metavar="HOUSE",
		help="Auction houses to run. Use 'all' to run every spider.",
	)
	parser.add_argument(
		"-s",
		"--skip",
		nargs="+",
		default=[],
		metavar="HOUSE",
		help="Auction houses to exclude from the selected set.",
	)
	return parser


def main() -> int:
	parser = _build_parser()
	args = parser.parse_args()

	include_values: list[str] = args.houses or []
	exclude_values: list[str] = args.skip or []

	# When invoked via `npm run spider --houses=val` (without --),
	# npm injects npm_config_houses=val as an env var into the child process.
	if not include_values:
		env_val = os.environ.get("npm_config_houses", "").strip()
		if env_val:
			include_values = [env_val]
	if not exclude_values:
		env_val = os.environ.get("npm_config_skip", "").strip()
		if env_val:
			exclude_values = [env_val]

	if not include_values:
		parser.error(
			"--houses is required.\n\n"
			f"  Run all:       npm run spider --houses=all\n"
			f"  Run some:      npm run spider --houses=zachys,tajan\n"
			f"  Exclude some:  npm run spider --houses=all --skip=zachys\n\n"
			f"Available houses: {', '.join(sorted(SPIDER_REGISTRY.keys()))}"
		)

	try:
		include_houses = _resolve_houses(include_values, "--houses")
		exclude_houses = _resolve_houses(exclude_values, "--skip")
	except ValueError as exc:
		parser.error(str(exc))

	if "all" in include_houses:
		selected = set(SPIDER_REGISTRY.keys())
	else:
		selected = include_houses

	if "all" in exclude_houses:
		exclude_houses = set(SPIDER_REGISTRY.keys())

	selected -= exclude_houses

	if not selected:
		parser.error("No spiders selected. Use --houses all or provide at least one valid house.")

	run_order = [name for name in SPIDER_REGISTRY if name in selected]
	skipped = [name for name in SPIDER_REGISTRY if name not in selected]

	print(f"Running spiders: {', '.join(run_order)}", flush=True)
	if skipped:
		print(f"Skipped spiders: {', '.join(skipped)}", flush=True)

	needs_async = any(name in PLAYWRIGHT_SPIDERS for name in run_order)
	settings = get_project_settings()
	if needs_async:
		process: CrawlerProcess | AsyncCrawlerProcess = AsyncCrawlerProcess(settings)
	else:
		process = CrawlerProcess(settings)

	for house in run_order:
		process.crawl(SPIDER_REGISTRY[house])

	process.start()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

