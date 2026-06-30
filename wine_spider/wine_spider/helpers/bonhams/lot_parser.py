from __future__ import annotations

import re
from dataclasses import dataclass

from parsel import Selector

from wine_spider.helpers.bonhams.multi_lot_spliter import split_title_by_valid_brackets
from wine_spider.helpers.bonhams.volume_parser import (
    extract_all_volume_units,
    parse_all_valid_quantity_volume,
)


@dataclass(frozen=True)
class BonhamsLotComponent:
    title: str
    producer: str | None
    vintage: str | None
    unit_format: str | None
    region: str | None


class BonhamsLotParser:
    _vintage_re = re.compile(r"\b(?:18|19|20)\d{2}\b")
    _volume_bracket_re = re.compile(r"\([^()]*\)")
    _catalog_component_re = re.compile(
        r"<B>(?P<title>.*?)</B>\s*<I>(?P<details>.*?)(?=<br\s*/?>\s*<B>|</div>|$)",
        re.IGNORECASE | re.DOTALL,
    )
    _region_re = re.compile(r"Region:\s*(?P<region>[^<]+)", re.IGNORECASE)

    _country_by_region = {
        "alsace": "France",
        "argentina": "Argentina",
        "australia": "Australia",
        "austria": "Austria",
        "barossa valley": "Australia",
        "bordeaux": "France",
        "burgundy": "France",
        "california": "United States",
        "champagne": "France",
        "chile": "Chile",
        "france": "France",
        "germany": "Germany",
        "italy": "Italy",
        "loire": "France",
        "madeira": "Portugal",
        "napa valley": "United States",
        "new zealand": "New Zealand",
        "piedmont": "Italy",
        "piemonte": "Italy",
        "portugal": "Portugal",
        "rhone": "France",
        "rhône": "France",
        "south africa": "South Africa",
        "spain": "Spain",
        "stellenbosch": "South Africa",
        "tuscany": "Italy",
        "usa": "United States",
    }

    def parse_components(
        self,
        title: str | None,
        catalog_desc: str | None = None,
    ) -> list[BonhamsLotComponent]:
        component_sources = self._extract_catalog_components(catalog_desc)
        if not component_sources:
            component_sources = [
                (component_title, None)
                for component_title in self._split_title_components(title or "")
            ]

        if not component_sources and title:
            component_sources = [(self._clean_text(title), None)]

        return [
            BonhamsLotComponent(
                title=component_title,
                producer=self.extract_producer(component_title),
                vintage=self.extract_vintage(component_title),
                unit_format=self.extract_unit_format(component_title),
                region=region,
            )
            for component_title, region in component_sources
            if component_title
        ]

    def infer_country(self, region: str | None) -> str | None:
        if not region:
            return None
        return self._country_by_region.get(region.strip().lower())

    def extract_producer(self, title: str | None) -> str | None:
        if not title:
            return None

        text = self._volume_bracket_re.sub("", title)
        text = re.sub(r"\bNV\b", "", text, flags=re.IGNORECASE)
        text = self._vintage_re.sub("", text)
        text = self._clean_text(text).strip(" ,-")
        if not text:
            return None

        producer = text.split(",", 1)[0].strip()
        return producer or None

    def extract_vintage(self, title: str | None) -> str | None:
        if not title:
            return None
        match = self._vintage_re.search(title)
        return match.group(0) if match else None

    def extract_unit_format(self, title: str | None) -> str | None:
        if not title:
            return None

        results = parse_all_valid_quantity_volume(title)
        if not results:
            results = extract_all_volume_units(title)
        return results[0][1] if results else None

    def _extract_catalog_components(
        self,
        catalog_desc: str | None,
    ) -> list[tuple[str, str | None]]:
        if not catalog_desc:
            return []

        components = []
        for match in self._catalog_component_re.finditer(catalog_desc):
            title = self._html_text(match.group("title"))
            details = match.group("details") or ""
            region_match = self._region_re.search(details)
            region = self._clean_text(region_match.group("region")) if region_match else None
            if title:
                components.append((title, region))

        if components:
            return components

        selector = Selector(text=catalog_desc)
        return [
            (self._clean_text(title), None)
            for title in selector.css("b::text, B::text").getall()
            if self._clean_text(title)
        ]

    def _split_title_components(self, title: str) -> list[str]:
        return [
            self._clean_text(f"{prefix} {bracket}")
            for prefix, bracket in split_title_by_valid_brackets(title or "")
        ]

    def _html_text(self, html: str) -> str:
        text = " ".join(Selector(text=html).css("::text").getall())
        return self._clean_text(text)

    def _clean_text(self, text: str | None) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
