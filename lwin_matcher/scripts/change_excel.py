import pandas as pd
import psycopg2

EXCEL_INPUT_PATH = "base_matches.xlsx"
EXCEL_OUTPUT_PATH = "base_matches_new.xlsx"

EXTERNAL_ID_COL = "lot_external_id"
LOT_NAME_COL = "sub_region"

def fix_mojibake(text):
    if not isinstance(text, str):
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text

df = pd.read_excel(EXCEL_INPUT_PATH)

df[EXTERNAL_ID_COL] = df[EXTERNAL_ID_COL].astype(str)

external_ids = df[EXTERNAL_ID_COL].dropna().unique().tolist()
print(f"Found {len(external_ids)} unique external_ids in Excel")

# 2. 查数据库（UTF8 完全正确）
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="wine_admin",
    user="postgres",
    password="341319",
    options="-c search_path=wine_admin"
)
conn.set_client_encoding("UTF8")

cur = conn.cursor()
cur.execute(
    """
    SELECT external_id, lot_name, li.wine_colour, li.lot_producer, l.sub_region
    FROM wine_admin.lots l JOIN wine_admin.lot_items li ON l.external_id = li.lot_id
    WHERE external_id = ANY(%s)
    """,
    (external_ids,)
)
rows = cur.fetchall()
cur.close()
conn.close()

id_to_lot_name = {
    str(ext): sub_region
    for ext, name, colour, lot_producer, sub_region in rows
    if name
}
print(list(id_to_lot_name.items())[10:20])

# 3. 用 DB 的干净值替换
df[LOT_NAME_COL] = df.apply(
    lambda r: id_to_lot_name.get(r[EXTERNAL_ID_COL], r.get(LOT_NAME_COL)),
    axis=1,
)

# 4. 修复历史 xls 里的乱码
# df[LOT_NAME_COL] = df[LOT_NAME_COL].apply(fix_mojibake)

# 5. 输出为 xlsx（彻底摆脱编码地雷）
df.to_excel(EXCEL_OUTPUT_PATH, index=False)

print(f"✅ Done. Saved to {EXCEL_OUTPUT_PATH}")
