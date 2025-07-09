import asyncio
import aiohttp
import math
import time
from database import LwinMatchingClient, LotsClient, LotItemsClient

lwin_client = LwinMatchingClient()
lots_client = LotsClient()
lot_items_client = LotItemsClient()

CONCURRENCY = 5              # 减小并发压力
BATCH_SIZE = 200             # 降低每批处理量
TOTAL_RECORDS = 807777
RETRY_LIMIT = 3              # 每个请求最多重试3次
RETRY_BACKOFF = 1.5          # 每次重试之间的退避倍数

sem = asyncio.Semaphore(CONCURRENCY)

async def lwin_match(session, payload, external_id):
    async with sem:
        retry = 0
        delay = 0.5  # 初始延迟，避免爆发式发送

        while retry <= RETRY_LIMIT:
            try:
                await asyncio.sleep(delay)  # 限速

                async with session.post("http://localhost:5000/match", json=payload) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        return (external_id, response_json)
                    else:
                        print(f"[HTTP ERROR] Status {response.status} for lot {external_id}")
                        return None

            except aiohttp.ClientConnectorError as e:
                retry += 1
                delay *= RETRY_BACKOFF
                print(f"[RETRY {retry}] Connection error for lot {external_id}: {e}")
                await asyncio.sleep(delay)

            except Exception as e:
                print(f"[FATAL ERROR] Unexpected error for lot {external_id}: {e}")
                return None

        print(f"[GIVE UP] Could not connect after {RETRY_LIMIT} retries for lot {external_id}")
        return None


async def process_batch(session, offset):
    lots = lots_client.query_lots_with_lot_items(limit=BATCH_SIZE, offset=offset)[0]
    tasks = []

    for lot in lots:
        for item in lot["lot_items"]:
            external_id = lot["external_id"]
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
            tasks.append(lwin_match(session, payload, external_id))

    results = await asyncio.gather(*tasks)
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
            try:
                lwin_client.upsert_by_external_id(data_dict)
            except Exception as e:
                print(f"[DB ERROR] Insert failed for {external_id}: {e}")
        else:
            print("No match found or error occurred.")


async def lwin_full_database_match():
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        for offset in range(0, TOTAL_RECORDS, BATCH_SIZE):
            print(f"\n🔄 Processing batch offset {offset}")
            await process_batch(session, offset)
            print(f"✅ Finished batch offset {offset}")


def clean_json_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_json_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_nan(i) for i in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    else:
        return obj


if __name__ == "__main__":
    asyncio.run(lwin_full_database_match())
