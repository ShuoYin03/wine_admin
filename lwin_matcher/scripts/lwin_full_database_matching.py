import os, sys
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(here, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "..")))
import asyncio
import math
import numpy as np
from shared.database.lwin_database_client import LwinDatabaseClient
from shared.database.lwin_matching_client import LwinMatchingClient
from shared.database.lots_client import LotsClient
from shared.database.lot_items_client import LotItemsClient
from app.models.lwin_matching_params import LwinMatchingParams
from app import create_app
from dotenv import load_dotenv
from app.service.lwin_matching_engine import LwinMatcherEngine

# --- Added imports for sample mode / CLI / CSV ---
import argparse
import csv
import os
import random
import functools
import traceback

load_dotenv()

lwin_client = LwinMatchingClient()
lots_client = LotsClient()
lot_items_client = LotItemsClient()
lwin_database_client = LwinDatabaseClient()

lwin_table = lwin_database_client.get_all()

lwin_service = LwinMatcherEngine(lwin_table)

CONCURRENCY = 10
BATCH_SIZE = 10000
TOTAL_RECORDS = 561072

sem = asyncio.Semaphore(CONCURRENCY)

LOT_FILTERS = [
    ("lot_type", "contains", "Wine"),
    ("lot_type", "contains", "wine"),
    ("lot_type", "contains", "Wine & Spirits"),
    ("lot_type", "contains", "White Wine"),
    ("lot_type", "contains", "Sweet Wine"),
    ("lot_type", "contains", "W"),
    ("lot_type", "contains", "Sparkling Wine"),
    ("lot_type", "contains", "Red Wine"),
    ("lot_type", "contains", "Rosé Wine"),
    ("lot_type", "contains", "Orange Wine"),
    ("lot_type", "contains", "Fruit Wine"),
    ("lot_type", "contains", "Fortified Wine"),
]

CSV_FIELD_ORDER = [
    # lot info
    "lot_external_id",
    "lot_name",
    "region",
    "sub_region",
    "country",
    # lot item info
    "lot_item_id",
    "lot_producer",
    "vintage",
    "colour",
    # match results
    "matched",
    "lwin_code",
    "lwin_11_code",
    "match_score",
    # top matched LWIN row snapshot
    "matched_ref_id",
    "matched_lwin",
    "matched_reference",
    "matched_display_name",
    "matched_producer_name",
    "matched_wine",
    "matched_colour",
    "matched_region",
    "matched_sub_region",
    "matched_country",
    "matched_classification",
]

async def lwin_match_direct(payload, external_id):
    async with sem:
        try:
            lwin_matching_params = LwinMatchingParams(
                wine_name=payload.get('wine_name', ''),
                lot_producer=payload.get('lot_producer', ''),
                vintage=payload.get('vintage', ''),
                region=payload.get('region', ''),
                sub_region=payload.get('sub_region', ''),
                country=payload.get('country', ''),
                colour=payload.get('colour', '')
            )

            matched, lwin_code, match_score, match_item = await asyncio.to_thread(
                lwin_service.match, lwin_matching_params, topk=1
            )

            for item in match_item:
                item['id'] = int(item['id'])
                item['lwin'] = int(item['lwin'])
                item['date_added'] = item['date_added'].isoformat()
                item['date_updated'] = item['date_updated'].isoformat()
                item['reference'] = int(float(item['reference'])) if item.get('reference') else None

            vintage = payload.get('vintage')
            lwin_11_code = None
            if lwin_code and vintage and isinstance(vintage, str) and len(vintage) == 4:
                if isinstance(lwin_code, list):
                    lwin_11_code = [int(str(code) + vintage) for code in lwin_code]
                else:
                    lwin_11_code = int(str(lwin_code) + vintage)

            return (external_id, {
                "matched": matched.value,
                "lwin_code": lwin_code,
                "lwin_11_code": lwin_11_code,
                "match_score": match_score,
                "match_item": match_item
            })

        except Exception as e:
            print(f"[ERROR] Matching error for lot {external_id}: {e}")
            print(f"[ERROR] Payload: {payload}")
            traceback.print_exc()
            return None

async def process_batch(offset):
    lots = lots_client.query_lots_with_items_and_auction(
        filters=LOT_FILTERS,
        order_by=["external_id"],
        limit=BATCH_SIZE,
        offset=offset
    )[0]

    tasks = []

    for lot in lots:
        for item in lot["lot_items"]:
            payload = {
                "wine_name": lot["lot_name"],
                "topk": 1,
                "lot_producer": item["lot_producer"],
                "vintage": item["vintage"],
                "region": lot["region"],
                "sub_region": lot["sub_region"],
                "country": lot["country"],
                "colour": item.get("colour"),
            }
            tasks.append(lwin_match_direct(payload, item['id']))

    results = await asyncio.gather(*tasks)

    data_dicts = []
    for result in results:
        if result:
            external_id, data = result
            data_dict = {
                "lot_id": external_id,
                "matched": data.get("matched"),
                "lwin": data.get("lwin_code"),
                "lwin_11": data.get("lwin_11_code"),
                "match_item": clean_json_nan(data.get("match_item")),
                "match_score": data.get("match_score"),
            }
            clean_data_dict = clean_json_nan(data_dict)
            data_dicts.append(clean_data_dict)
        else:
            print(f"[FAIL] Matching failed or skipped for one item.")

    try:
        inserted_count = lwin_client.bulk_insert(data_dicts)
        print(f"[DB] Bulk inserted {inserted_count} rows for batch offset {offset}")
    except Exception as e:
        print(f"[DB ERROR] Bulk insert failed for batch offset {offset}: {e}")

async def lwin_full_database_match(start_offset: int = 0):
    if start_offset < 0:
        start_offset = 0
    if start_offset % BATCH_SIZE != 0:
        print(f"[WARN] start_offset {start_offset} is not aligned to BATCH_SIZE {BATCH_SIZE}. It will still run.")
    for offset in range(start_offset, TOTAL_RECORDS, BATCH_SIZE):
        print(f"\n🔄 Processing batch offset {offset}")
        await process_batch(offset)
        print(f"✅ Finished batch offset {offset}")

# ------------------- Sample mode helpers -------------------
async def fetch_lot_at_offset(offset: int):
    """Fetch a single lot (with items and auction) at a specific offset using current filters.
    Uses a thread to avoid blocking the event loop if the client is synchronous.
    """
    try:
        func = functools.partial(
            lots_client.query_lots_with_items_and_auction,
            filters=LOT_FILTERS,
            order_by=["external_id"],
            limit=1,
            offset=offset,
        )
        result = await asyncio.to_thread(func)
        lots = result[0]
        return lots[0] if lots else None
    except Exception as e:
        print(f"[ERROR] Fetch lot at offset {offset} failed: {e}")
        return None

def export_rows_to_csv(rows, path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not rows:
        # Write only headers in required order
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELD_ORDER)
            writer.writeheader()
        print(f"[CSV] No rows. Wrote header only at {path}")
        return
    # Use fixed header order exactly as specified
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELD_ORDER, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"[CSV] Wrote {len(rows)} rows to {path}")

async def lwin_sample_match(sample_size: int, output_csv: str, total_records: int, seed: int = 42):
    if sample_size <= 0:
        print("[SAMPLE] sample-size must be > 0")
        return
    if sample_size > total_records:
        print("[SAMPLE] sample-size cannot exceed total-records")
        return

    rng = random.Random(seed)
    offsets = sorted(rng.sample(range(total_records), sample_size))
    print(f"[SAMPLE] Sampling {sample_size} lots from {total_records} total records (seed={seed})")

    # Fetch sampled lots concurrently
    lot_tasks = [fetch_lot_at_offset(o) for o in offsets]
    sampled_lots = [lot for lot in await asyncio.gather(*lot_tasks) if lot]

    # Build match tasks for each lot item
    item_index = {}
    match_tasks = []
    for lot in sampled_lots:
        for item in lot.get("lot_items", []):
            payload = {
                "wine_name": lot.get("lot_name"),
                "topk": 1,
                "lot_producer": item.get("lot_producer"),
                "vintage": item.get("vintage"),
                "region": lot.get("region"),
                "sub_region": lot.get("sub_region"),
                "country": lot.get("country"),
                "colour": item.get("colour"),
            }
            external_id = item["id"]
            item_index[external_id] = (lot, item)
            match_tasks.append(lwin_match_direct(payload, external_id))

    results = await asyncio.gather(*match_tasks, return_exceptions=False)

    # Flatten rows for CSV
    rows = []
    for result in results:
        if not result:
            continue
        external_id, data = result
        lot, item = item_index.get(external_id, ({}, {}))

        matched_items = data.get("match_item") or []
        top = matched_items[0] if matched_items else {}

        row = {
            # lot info
            "lot_external_id": lot.get("external_id"),
            "lot_name": lot.get("lot_name"),
            "region": lot.get("region"),
            "sub_region": lot.get("sub_region"),
            "country": lot.get("country"),
            # lot item info
            "lot_item_id": external_id,
            "lot_producer": item.get("lot_producer"),
            "vintage": item.get("vintage"),
            "colour": item.get("colour"),
            # match results
            "matched": data.get("matched"),
            "lwin_code": data.get("lwin_code"),
            "lwin_11_code": data.get("lwin_11_code"),
            "match_score": data.get("match_score"),
            # top matched LWIN row snapshot
            "matched_ref_id": top.get("id"),
            "matched_lwin": top.get("lwin"),
            "matched_reference": top.get("reference"),
            "matched_display_name": top.get("display_name"),
            "matched_producer_name": top.get("producer_name"),
            "matched_wine": top.get("wine"),
            "matched_colour": top.get("colour"),
            "matched_region": top.get("region"),
            "matched_sub_region": top.get("sub_region"),
            "matched_country": top.get("country"),
            "matched_classification": top.get("classification"),
        }
        rows.append(clean_json_nan(row))

    export_rows_to_csv(rows, output_csv)

def clean_json_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_json_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_nan(i) for i in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    else:
        return obj

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LWIN database matching")
    parser.add_argument("--mode", choices=["full", "sample"], default="full", help="full: process batches; sample: random N lots to CSV")
    parser.add_argument("--sample-size", type=int, default=100, help="number of lots to sample when mode=sample")
    parser.add_argument("--output", type=str, default=os.path.join(os.getcwd(), "sample_matches.csv"), help="CSV output path for sample mode")
    parser.add_argument("--seed", type=int, default=42, help="random seed for sampling")
    parser.add_argument("--total-records", type=int, default=TOTAL_RECORDS, help="override total records if unknown")
    parser.add_argument("--start-offset", type=int, default=0, help="start offset for full mode")
    args = parser.parse_args()

    if args.mode == "sample":
        asyncio.run(lwin_sample_match(args.sample_size, args.output, args.total_records, args.seed))
    else:
        asyncio.run(lwin_full_database_match(args.start_offset))
