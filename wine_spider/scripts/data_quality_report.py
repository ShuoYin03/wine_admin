"""
Data Quality Report — per auction house
Run: D:\Anaconda\envs\wine_admin\python.exe scripts/data_quality_report.py
"""
from __future__ import annotations

import sys
import psycopg2
import psycopg2.extras

DB_URL = "postgresql://postgres:341319@localhost:5432/wine_admin"
DB_OPTIONS = "-csearch_path=wine_admin"

AUCTION_NULLABLE_FIELDS = [
    "auction_title", "city", "continent",
    "start_date", "end_date", "year", "quarter",
    "auction_type", "url",
]
AUCTION_SALES_NULLABLE_FIELDS = [
    "lots", "sold", "currency",
    "total_low_estimate", "total_high_estimate",
    "total_sales", "volume_sold",
    "top_lot", "sale_type",
]
LOT_NULLABLE_FIELDS = [
    "lot_name", "lot_type", "volume", "unit",
    "original_currency", "start_price", "end_price",
    "low_estimate", "high_estimate",
    "sold", "sold_date", "region", "sub_region",
    "country", "success", "url",
]
LOT_ITEM_NULLABLE_FIELDS = ["lot_producer", "vintage", "unit_format", "wine_colour"]


def pct(n: int, total: int) -> str:
    if total == 0:
        return "  —  "
    return f"{n / total * 100:5.1f}%"


def bar(p: float, width: int = 18) -> str:
    filled = round(p / 100 * width)
    return "█" * filled + "░" * (width - filled)


def section(title: str) -> None:
    print(f"\n{'═' * 70}\n  {title}\n{'═' * 70}")


def subsection(title: str) -> None:
    print(f"\n  ── {title} ──")


def null_table(rows: list[tuple[str, int, int]], label_width: int = 28) -> None:
    for field, null_count, total in rows:
        p = null_count / total * 100 if total else 0
        print(f"    {field:<{label_width}} {null_count:>6} / {total:<6}  {pct(null_count, total)}  {bar(p)}")


def main() -> None:
    try:
        conn = psycopg2.connect(DB_URL, options=DB_OPTIONS)
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}", file=sys.stderr)
        sys.exit(1)

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT DISTINCT auction_house FROM auctions ORDER BY auction_house")
    houses: list[str] = [r["auction_house"] for r in cur.fetchall()]

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "  WINE ADMIN — DATA QUALITY REPORT".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # global summary
    cur.execute("SELECT COUNT(*) FROM auctions");  total_auctions = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM lots");       total_lots     = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM lot_items");  total_items    = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM auction_sales"); total_sales = cur.fetchone()[0]

    section("GLOBAL SUMMARY")
    print(f"    Auction houses : {len(houses)}")
    print(f"    Auctions       : {total_auctions:,}")
    print(f"    Auction sales  : {total_sales:,}  (coverage {pct(total_sales, total_auctions)})")
    print(f"    Lots           : {total_lots:,}")
    print(f"    Lot items      : {total_items:,}  (coverage {pct(total_items, total_lots)})")

    for house in houses:
        section(f"AUCTION HOUSE: {house}")

        # ── auctions ──────────────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM auctions WHERE auction_house = %s", (house,))
        n_auctions: int = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM auction_sales s "
            "JOIN auctions a ON a.external_id = s.auction_id "
            "WHERE a.auction_house = %s", (house,))
        n_sales: int = cur.fetchone()[0]

        subsection(f"Auctions  (total: {n_auctions})")
        print(f"    auction_sales coverage : {n_sales} / {n_auctions}  {pct(n_sales, n_auctions)}")

        null_rows = []
        for f in AUCTION_NULLABLE_FIELDS:
            cur.execute(f"SELECT COUNT(*) FROM auctions WHERE auction_house = %s AND {f} IS NULL", (house,))
            null_rows.append((f, cur.fetchone()[0], n_auctions))
        null_table(null_rows)

        cur.execute(
            "SELECT COUNT(*) FROM auctions WHERE auction_house = %s "
            "AND end_date IS NOT NULL AND start_date IS NOT NULL AND end_date < start_date", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  end_date < start_date : {v}")

        cur.execute(
            "SELECT COUNT(*) FROM auctions WHERE auction_house = %s "
            "AND start_date IS NOT NULL AND year IS NOT NULL "
            "AND EXTRACT(YEAR FROM start_date) != year", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  year ≠ EXTRACT(year FROM start_date) : {v}")

        # ── auction_sales ─────────────────────────────────────────────────
        if n_sales > 0:
            subsection(f"Auction Sales  (total: {n_sales})")
            null_rows = []
            for f in AUCTION_SALES_NULLABLE_FIELDS:
                cur.execute(
                    f"SELECT COUNT(*) FROM auction_sales s "
                    f"JOIN auctions a ON a.external_id = s.auction_id "
                    f"WHERE a.auction_house = %s AND s.{f} IS NULL", (house,))
                null_rows.append((f, cur.fetchone()[0], n_sales))
            null_table(null_rows)

            cur.execute(
                "SELECT COUNT(*) FROM auction_sales s "
                "JOIN auctions a ON a.external_id = s.auction_id "
                "WHERE a.auction_house = %s AND s.sold IS NOT NULL AND s.lots IS NOT NULL AND s.sold > s.lots",
                (house,))
            if (v := cur.fetchone()[0]):
                print(f"    ⚠  sold > lots : {v}")

            cur.execute(
                "SELECT COUNT(*) FROM auction_sales s "
                "JOIN auctions a ON a.external_id = s.auction_id "
                "WHERE a.auction_house = %s AND s.total_sales < 0", (house,))
            if (v := cur.fetchone()[0]):
                print(f"    ⚠  total_sales < 0 : {v}")

        # ── lots ──────────────────────────────────────────────────────────
        cur.execute(
            "SELECT COUNT(*) FROM lots l "
            "JOIN auctions a ON a.external_id = l.auction_id WHERE a.auction_house = %s", (house,))
        n_lots: int = cur.fetchone()[0]

        if n_lots == 0:
            print("\n    (no lots for this house)")
            continue

        cur.execute(
            "SELECT COUNT(DISTINCT l.external_id) FROM lot_items li "
            "JOIN lots l ON l.external_id = li.lot_id "
            "JOIN auctions a ON a.external_id = l.auction_id WHERE a.auction_house = %s", (house,))
        n_lots_with_items: int = cur.fetchone()[0]

        subsection(f"Lots  (total: {n_lots:,})")
        print(f"    lot_items coverage : {n_lots_with_items:,} / {n_lots:,}  {pct(n_lots_with_items, n_lots)}")

        null_rows = []
        for f in LOT_NULLABLE_FIELDS:
            cur.execute(
                f"SELECT COUNT(*) FROM lots l "
                f"JOIN auctions a ON a.external_id = l.auction_id "
                f"WHERE a.auction_house = %s AND l.{f} IS NULL", (house,))
            null_rows.append((f, cur.fetchone()[0], n_lots))
        null_table(null_rows)

        cur.execute(
            "SELECT COUNT(*) FROM lots l JOIN auctions a ON a.external_id = l.auction_id "
            "WHERE a.auction_house = %s AND l.end_price IS NOT NULL AND l.end_price < 0", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  end_price < 0 : {v}")

        cur.execute(
            "SELECT COUNT(*) FROM lots l JOIN auctions a ON a.external_id = l.auction_id "
            "WHERE a.auction_house = %s AND l.low_estimate IS NOT NULL AND l.high_estimate IS NOT NULL "
            "AND l.high_estimate < l.low_estimate", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  high_estimate < low_estimate : {v}")

        cur.execute(
            "SELECT COUNT(*) FROM lots l JOIN auctions a ON a.external_id = l.auction_id "
            "WHERE a.auction_house = %s AND l.sold = TRUE AND l.end_price IS NULL", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  sold=TRUE but end_price NULL : {v}")

        cur.execute(
            "SELECT COUNT(*) FROM lots l JOIN auctions a ON a.external_id = l.auction_id "
            "WHERE a.auction_house = %s AND l.sold_date IS NOT NULL "
            "AND a.start_date IS NOT NULL AND a.end_date IS NOT NULL "
            "AND (l.sold_date < a.start_date OR l.sold_date > a.end_date)", (house,))
        if (v := cur.fetchone()[0]):
            print(f"    ⚠  sold_date outside auction date range : {v}")

        # ── lot_items ─────────────────────────────────────────────────────
        cur.execute(
            "SELECT COUNT(*) FROM lot_items li "
            "JOIN lots l ON l.external_id = li.lot_id "
            "JOIN auctions a ON a.external_id = l.auction_id WHERE a.auction_house = %s", (house,))
        n_items: int = cur.fetchone()[0]

        if n_items > 0:
            subsection(f"Lot Items  (total: {n_items:,})")
            null_rows = []
            for f in LOT_ITEM_NULLABLE_FIELDS:
                cur.execute(
                    f"SELECT COUNT(*) FROM lot_items li "
                    f"JOIN lots l ON l.external_id = li.lot_id "
                    f"JOIN auctions a ON a.external_id = l.auction_id "
                    f"WHERE a.auction_house = %s AND li.{f} IS NULL", (house,))
                null_rows.append((f, cur.fetchone()[0], n_items))
            null_table(null_rows)

            # unusual vintage values
            cur.execute(
                "SELECT COUNT(*) FROM lot_items li "
                "JOIN lots l ON l.external_id = li.lot_id "
                "JOIN auctions a ON a.external_id = l.auction_id "
                "WHERE a.auction_house = %s AND li.vintage IS NOT NULL "
                "AND li.vintage !~ '^[0-9]{4}$' "
                "AND LOWER(li.vintage) NOT IN ('nv','n/v','non-vintage','mv','multivintage')", (house,))
            bad_v: int = cur.fetchone()[0]
            if bad_v:
                cur.execute(
                    "SELECT DISTINCT li.vintage FROM lot_items li "
                    "JOIN lots l ON l.external_id = li.lot_id "
                    "JOIN auctions a ON a.external_id = l.auction_id "
                    "WHERE a.auction_house = %s AND li.vintage IS NOT NULL "
                    "AND li.vintage !~ '^[0-9]{4}$' "
                    "AND LOWER(li.vintage) NOT IN ('nv','n/v','non-vintage','mv','multivintage') LIMIT 10",
                    (house,))
                samples = [r[0] for r in cur.fetchall()]
                print(f"    ⚠  unusual vintage values : {bad_v}  e.g. {samples}")

            cur.execute(
                "SELECT COUNT(*) FROM lot_items li "
                "JOIN lots l ON l.external_id = li.lot_id "
                "JOIN auctions a ON a.external_id = l.auction_id "
                "WHERE a.auction_house = %s AND li.vintage ~ '^[0-9]{4}$' "
                "AND li.vintage::int NOT BETWEEN 1800 AND EXTRACT(YEAR FROM NOW())::int", (house,))
            if (v := cur.fetchone()[0]):
                print(f"    ⚠  vintage out of range [1800–now] : {v}")

    cur.close()
    conn.close()
    print(f"\n{'═' * 70}\n  Report complete.\n{'═' * 70}\n")


if __name__ == "__main__":
    main()
