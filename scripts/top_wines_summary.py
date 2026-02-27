from __future__ import annotations

import os
import pandas as pd
import psycopg2


SQL_TOP_PRODUCERS = """
SELECT
    COALESCE(li.lot_producer, '(unknown)') AS producer,
    COUNT(*) AS lot_items
FROM lots l
LEFT JOIN lot_items li ON li.lot_id = l.external_id
GROUP BY COALESCE(li.lot_producer, '(unknown)')
ORDER BY lot_items DESC
LIMIT %s;
"""

SQL_TOP_LOT_NAMES = """
SELECT
    l.lot_name,
    COUNT(*) AS lots
FROM lots l
GROUP BY l.lot_name
ORDER BY lots DESC
LIMIT %s;
"""


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

    out_dir = os.path.join(os.path.dirname(__file__), "export_wines_last5y", "db_overview")
    os.makedirs(out_dir, exist_ok=True)

    with psycopg2.connect(**conn_params) as conn:
        top_producers = pd.read_sql_query(SQL_TOP_PRODUCERS, conn, params=(200,))
        top_lot_names = pd.read_sql_query(SQL_TOP_LOT_NAMES, conn, params=(200,))

    top_producers_path = os.path.join(out_dir, "top_producers.csv")
    top_lot_names_path = os.path.join(out_dir, "top_lot_names.csv")

    top_producers.to_csv(top_producers_path, index=False, encoding="utf-8-sig")
    top_lot_names.to_csv(top_lot_names_path, index=False, encoding="utf-8-sig")

    print(f"Top producers -> {top_producers_path}")
    print(f"Top lot names -> {top_lot_names_path}")


if __name__ == "__main__":
    main()
