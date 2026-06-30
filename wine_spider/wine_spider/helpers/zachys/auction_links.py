from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup


AUCTION_LANDING_URL = "https://auction.zachys.com/"
ZACHYS_BID_BASE_URL = "https://bid.zachys.com"

CATALOG_URL_RE = re.compile(
    r"/auctions/catalog/id/(?P<auction_id>\d+)/(?P<auction_seo_name>[^/?#]+)"
)

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_PATTERN = "|".join(month.title() for month in MONTHS)
START_DATE_RE = re.compile(rf"\b(?P<month>{MONTH_PATTERN})\s+(?P<day>\d{{1,2}})\b")
END_DATE_RE = re.compile(
    rf"(?:-|&|and)\s*(?:(?P<month>{MONTH_PATTERN})\s+)?(?P<day>\d{{1,2}})\b"
)


@dataclass(frozen=True)
class ZachysCatalogLink:
    auction_id: str
    auction_seo_name: str
    catalog_url: str
    title: str
    city: str | None
    start_date: str | None
    end_date: str | None
    year: int | None
    quarter: int | None


def parse_zachys_catalog_url(url: str) -> tuple[str, str] | None:
    match = CATALOG_URL_RE.search(url)
    if not match:
        return None
    return match.group("auction_id"), match.group("auction_seo_name")


def build_zachys_categories_url(auction_id: str | int) -> str:
    return (
        f"{ZACHYS_BID_BASE_URL}/search/get-categories"
        f"?auction_id={auction_id}&page_type=catalog-list&is_more=0"
    )


def extract_zachys_lot_count_from_categories(payload: dict) -> int:
    categories = (payload.get("payload") or {}).get("categories") or []
    counts = []
    for category in categories:
        try:
            counts.append(int(category.get("lots_qty") or 0))
        except (TypeError, ValueError):
            continue
    return max(counts) if counts else 0


def extract_zachys_past_catalog_links(
    html: str,
    base_url: str = AUCTION_LANDING_URL,
    current_year: int | None = None,
) -> list[ZachysCatalogLink]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[ZachysCatalogLink] = []
    seen_auction_ids: set[str] = set()

    sections = _latest_results_sections(soup) or soup.select(".past-auctions")
    for section in sections:
        for anchor in section.select('a[href*="/auctions/catalog/id/"]'):
            href = anchor.get("href") or ""
            catalog_url = urljoin(base_url, href)
            parsed = parse_zachys_catalog_url(catalog_url)
            if parsed is None:
                continue

            auction_id, auction_seo_name = parsed
            if auction_id in seen_auction_ids:
                continue
            seen_auction_ids.add(auction_id)

            title = _extract_auction_title(anchor) or _title_from_slug(auction_seo_name)
            start_date, end_date, year, quarter = infer_zachys_auction_dates(
                title,
                current_year=current_year,
            )

            links.append(
                ZachysCatalogLink(
                    auction_id=auction_id,
                    auction_seo_name=auction_seo_name,
                    catalog_url=catalog_url,
                    title=title,
                    city=infer_zachys_city(title),
                    start_date=start_date,
                    end_date=end_date,
                    year=year,
                    quarter=quarter,
                )
            )

    return links


def infer_zachys_city(title: str) -> str | None:
    parts = [part.strip() for part in title.split(",") if part.strip()]
    if len(parts) >= 2:
        return parts[-2]
    return None


def infer_zachys_auction_dates(
    title: str,
    current_year: int | None = None,
) -> tuple[str | None, str | None, int | None, int | None]:
    year = current_year or datetime.now(UTC).year
    start_match = START_DATE_RE.search(title)
    if not start_match:
        return None, None, None, None

    start_month = MONTHS[start_match.group("month").lower()]
    start_day = int(start_match.group("day"))
    end_month = start_month
    end_day = start_day

    tail = title[start_match.end() : start_match.end() + 40]
    end_match = END_DATE_RE.search(tail)
    if end_match:
        end_day = int(end_match.group("day"))
        if end_match.group("month"):
            end_month = MONTHS[end_match.group("month").lower()]

    try:
        start = date(year, start_month, start_day)
        end = date(year, end_month, end_day)
    except ValueError:
        return None, None, None, None

    return start.isoformat(), end.isoformat(), start.year, (start.month - 1) // 3 + 1


def _latest_results_sections(soup: BeautifulSoup) -> list:
    sections = []
    for heading in soup.find_all(["h1", "h2", "h3"]):
        if _clean_text(heading.get_text(" ", strip=True)).lower() != "latest auction results":
            continue

        section = None
        node = heading
        while node.parent is not None and getattr(node.parent, "name", None) not in {
            "body",
            "html",
            "[document]",
        }:
            candidate = node.parent
            headings = [
                _clean_text(h.get_text(" ", strip=True)).lower()
                for h in candidate.find_all(["h1", "h2", "h3"])
            ]
            if "upcoming auctions" in headings:
                break
            if candidate.select('a[href*="/auctions/catalog/id/"]'):
                section = candidate
            node = candidate

        if section is not None:
            sections.append(section)

    return sections


def _extract_auction_title(anchor) -> str:
    tile = anchor.find_parent(
        lambda tag: bool(tag and "upcoming-auction-item" in (tag.get("class") or []))
    )
    if tile is not None:
        title_element = tile.select_one(".upcoming-auction-text")
        title = _clean_text(title_element.get_text(" ", strip=True)) if title_element else ""
        if title:
            return title
        title = _clean_text(tile.get_text(" ", strip=True))
        if title:
            return title

    return _clean_text(anchor.get_text(" ", strip=True))


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").strip()


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())
