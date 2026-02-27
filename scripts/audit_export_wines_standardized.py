from __future__ import annotations

import os
import random
import re
import unicodedata
from typing import Iterable

import pandas as pd
import psycopg2


WINES = {
    "Mouton Rothschild": [
        "Mouton Rothschild",
        "Mouton-Rothschild",
        "Ch. Mouton Rothschild",
        "Ch. Mouton-Rothschild",
        "Chateau Mouton Rothschild",
        "Château Mouton Rothschild",
        "Chateau Mouton-Rothschild",
        "Château Mouton-Rothschild",
        "Chateau+Mouton-Rothschild",
        "Chateau+Mouton+Rothschild",
        "Chateau+Mouton Rothschild",
        "Chateau Mouton+Rothschild",
        "Château+Mouton+Rothschild",
        "Château+Mouton Rothschild",
        "Château Mouton+Rothschild",
    ],
    "Lafite Rothschild": [
        "Lafite Rothschild",
        "Lafite-Rothschild",
        "Ch. Lafite Rothschild",
        "Ch. Lafite-Rothschild",
        "Chateau Lafite Rothschild",
        "Château Lafite Rothschild",
        "Chateau Lafite-Rothschild",
        "Château Lafite-Rothschild",
        "Chateau+Lafite-Rothschild",
        "Chateau+Lafite+Rothschild",
        "Chateau+Lafite Rothschild",
        "Chateau Lafite+Rothschild",
        "Château+Lafite+Rothschild",
        "Château+Lafite Rothschild",
        "Château Lafite+Rothschild",
    ],
    "Latour": [
        "Latour",
        "Ch. Latour",
        "Chateau Latour",
        "Château Latour",
        "Chateau+Latour",
    ],
    "Margaux": [
        "Margaux",
        "Ch. Margaux",
        "Chateau Margaux",
        "Château Margaux",
        "Chateau+Margaux",
    ],
    "Haut Brion": [
        "Haut Brion",
        "Haut-Brion",
        "Ch. Haut Brion",
        "Ch. Haut-Brion",
        "Chateau Haut Brion",
        "Château Haut Brion",
        "Chateau Haut-Brion",
        "Château Haut-Brion",
        "Chateau+Haut-Brion",
        "Chateau+Haut+Brion",
        "Chateau+Haut Brion",
        "Château+Haut+Brion",
        "Château+Haut Brion",
    ],
    "Cheval Blanc": [
        "Cheval Blanc",
        "Ch. Cheval Blanc",
        "Chateau Cheval Blanc",
        "Château Cheval Blanc",
        "Chateau+Cheval+Blanc",
        "Chateau+Cheval Blanc",
        "Château+Cheval+Blanc",
        "Château+Cheval Blanc",
    ],
    "Petrus": [
        "Petrus",
        "Pétrus",
        "Ch. Petrus",
        "Ch. Pétrus",
        "Chateau Petrus",
        "Château Petrus",
        "Chateau Pétrus",
        "Château Pétrus",
        "Chateau+Petrus",
        "Chateau+Pétrus",
        "Château+Petrus",
        "Château+Pétrus",
    ],
    "Domaine de la Romanée Conti": [
        "Domaine de la Romanée Conti",
        "Domaine de la Romanee Conti",
        "Domaine de la Romanée-Conti",
        "Domaine de la Romanee-Conti",
        "Domaine Romanée Conti",
        "Domaine Romanee Conti",
        "Domaine Romanée-Conti",
        "Domaine Romanee-Conti",
        "Dom. de la Romanée Conti",
        "Dom. de la Romanee Conti",
        "Dom. de la Romanée-Conti",
        "Dom. de la Romanee-Conti",
        "Romanée Conti",
        "Romanee Conti",
        "Romanée-Conti",
        "Romanee-Conti",
        "DRC",
        "D.R.C.",
        "Domaine+de+la+Romanee-Conti",
        "Domaine+de+la+Roman%C3%A9e-Conti",
        "Domaine+de+la+Romanee+Conti",
        "Domaine+de+la+Roman%C3%A9e+Conti",
    ],
    "Masseto": ["Masseto"],
    "Sassicaia": ["Sassicaia"],
}


def normalize_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|]", "_", value)
    value = re.sub(r"\s+", " ", value)
    return value


def standardize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("+", " ").lower()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_standardized_patterns(patterns: Iterable[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for pattern in patterns:
        standardized = standardize_text(pattern)
        if standardized and standardized not in seen:
            seen.add(standardized)
            result.append(standardized)
    return result


def row_matches(patterns: list[str], lot_name: str, lot_producer: str) -> bool:
    if not patterns:
        return False
    for pattern in patterns:
        if pattern in lot_name or pattern in lot_producer:
            return True
    return False


def build_suspect_tokens(wine_name: str, patterns: Iterable[str]) -> list[str]:
    base = standardize_text(wine_name)
    tokens = {t for t in base.split() if len(t) >= 4}
    for pattern in patterns:
        standardized = standardize_text(pattern)
        tokens.update(t for t in standardized.split() if len(t) >= 4)
    return sorted(tokens)


def main() -> None:
    # TODO: Replace with your real connection parameters
    conn_params = {
        "host": "localhost",
        "port": 5432,
        "database": "wine_admin",
        "user": "postgres",
        "password": "341319",
        "options": "-c search_path=wine_admin",
    }

    out_dir = os.path.join(os.path.dirname(__file__), "export_wines_standardized_audit")
    os.makedirs(out_dir, exist_ok=True)

    with psycopg2.connect(**conn_params) as conn:
        lots = pd.read_sql_query(
            """
            SELECT
                l.external_id AS lot_external_id,
                l.lot_name,
                l.lot_type,
                l.volume,
                l.unit,
                l.original_currency,
                l.start_price,
                l.end_price,
                l.low_estimate,
                l.high_estimate,
                l.sold,
                l.sold_date,
                l.region,
                l.sub_region,
                l.country,
                l.url AS lot_url,
                l.auction_id
            FROM lots l
            """,
            conn,
        )
        auctions = pd.read_sql_query(
            """
            SELECT
                a.external_id AS auction_external_id,
                a.auction_title,
                a.auction_house,
                a.city,
                a.continent,
                a.start_date,
                a.end_date,
                a.year,
                a.quarter,
                a.auction_type,
                a.url AS auction_url
            FROM auctions a
            """,
            conn,
        )
        lot_items = pd.read_sql_query(
            """
            SELECT
                li.lot_id AS lot_external_id,
                li.lot_producer,
                li.vintage,
                li.unit_format,
                li.wine_colour
            FROM lot_items li
            """,
            conn,
        )

    df = lots.merge(auctions, left_on="auction_id", right_on="auction_external_id", how="inner")
    df = df.drop(columns=["auction_id", "auction_external_id"], errors="ignore")
    df = df.merge(lot_items, on="lot_external_id", how="left")

    df["sold_date"] = pd.to_datetime(df["sold_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")

    effective_date = df["sold_date"].fillna(df["end_date"]).fillna(df["start_date"])
    cutoff_date = pd.Timestamp.today().normalize() - pd.DateOffset(years=5)
    df = df[effective_date >= cutoff_date].copy()

    df["lot_name_std"] = df["lot_name"].map(standardize_text)
    df["lot_producer_std"] = df["lot_producer"].map(standardize_text)

    summary_rows: list[dict[str, object]] = []

    for wine_name, patterns in WINES.items():
        standardized_patterns = build_standardized_patterns([wine_name, *patterns])
        tokens = build_suspect_tokens(wine_name, patterns)

        matched_mask = df.apply(
            lambda row: row_matches(
                standardized_patterns,
                row["lot_name_std"],
                row["lot_producer_std"],
            ),
            axis=1,
        )
        matched = df[matched_mask].copy()

        tokens_pattern = "|".join(re.escape(token) for token in tokens)
        if tokens_pattern:
            token_mask = (
                df["lot_name_std"].str.contains(tokens_pattern, na=False)
                | df["lot_producer_std"].str.contains(tokens_pattern, na=False)
            )
        else:
            token_mask = pd.Series(False, index=df.index)

        suspects = df[token_mask & ~matched_mask].copy()

        summary_rows.append(
            {
                "wine_name": wine_name,
                "patterns_count": len(standardized_patterns),
                "tokens": " ".join(tokens),
                "matched_rows": len(matched),
                "matched_lots": matched["lot_external_id"].nunique(dropna=True),
                "suspect_rows": len(suspects),
            }
        )

        safe_name = normalize_filename(wine_name)
        sample_path = os.path.join(out_dir, f"audit_samples_{safe_name}.csv")
        suspect_path = os.path.join(out_dir, f"audit_suspects_{safe_name}.csv")

        matched.sample(min(50, len(matched)), random_state=42).to_csv(
            sample_path, index=False, encoding="utf-8-sig"
        )

        if len(suspects) > 0:
            suspects.sample(min(200, len(suspects)), random_state=42).to_csv(
                suspect_path, index=False, encoding="utf-8-sig"
            )
        else:
            pd.DataFrame(columns=df.columns).to_csv(
                suspect_path, index=False, encoding="utf-8-sig"
            )

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(
        os.path.join(out_dir, "audit_summary.csv"), index=False, encoding="utf-8-sig"
    )

    print(f"Audit files written to: {out_dir}")


if __name__ == "__main__":
    main()
