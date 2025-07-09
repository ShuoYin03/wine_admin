import asyncio
import math
import time
import numpy as np
from database import LwinMatchingClient, LotsClient, LotItemsClient
from app.model import LwinMatchingParams
from app import create_app

app = create_app()
lwin_client = LwinMatchingClient()
lots_client = LotsClient()
lot_items_client = LotItemsClient()

CONCURRENCY = 10
BATCH_SIZE = 10000
TOTAL_RECORDS = 807777

sem = asyncio.Semaphore(CONCURRENCY)

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
                app.lwin_matching_service.match, lwin_matching_params, topk=1
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
            return None


async def process_batch(offset):
    lots = lots_client.query_lots_with_lot_items(
        filters=[
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
        ],
        order_by=["external_id"],
        limit=BATCH_SIZE,
        offset=offset
    )[0]

    # existing_lwin_ids = lwin_client.get_all_lot_ids()
    # lots = [lot for lot in lots if lot["external_id"] not in existing_lwin_ids]
    # print(f"Filtered {len(lots)} lots for processing.")

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
    # for result in results:
    #     if result:
    #         external_id, data = result
    #         data_dict = {
    #             "lot_id": external_id,
    #             "matched": data.get("matched"),
    #             "lwin": data.get("lwin_code"),
    #             "lwin_11": data.get("lwin_11_code"),
    #             "match_item": clean_json_nan(data.get("match_item")),
    #             "match_score": data.get("match_score"),
    #         }
    #         clean_data_dict = clean_json_nan(data_dict)
    #         try:
    #             lwin_client.upsert_by_external_id(clean_data_dict)
    #         except Exception as e:
    #             print(f"[DB ERROR] Insert failed for {external_id}: {e}")
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

async def lwin_full_database_match():
    for offset in range(0, TOTAL_RECORDS, BATCH_SIZE):
        print(f"\n🔄 Processing batch offset {offset}")
        await process_batch(offset)
        print(f"✅ Finished batch offset {offset}")


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
    app = create_app()
    with app.app_context():
        asyncio.run(lwin_full_database_match())
