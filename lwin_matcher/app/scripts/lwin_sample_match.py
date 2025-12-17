# import asyncio
# import json
# import math
# import os
# import pandas as pd
# from datetime import date, datetime
# from typing import List
# import argparse
# import numpy as np
# from dotenv import load_dotenv
# from openai import OpenAI
# from pydantic import BaseModel

# from database import LwinMatchingClient, LotsClient, LotItemsClient, LwinDatabaseClient
# from lwin_matcher.app.model import LwinMatchingParams
# from lwin_matcher.app.service.lwin_matching_engine import LwinMatcherEngine

# # --- Config ---
# load_dotenv()

# # --- Clients ---
# lwin_client = LwinMatchingClient()
# lwin_database_client = LwinDatabaseClient()
# lots_client = LotsClient()
# lot_items_client = LotItemsClient()
# chatgpt = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # --- Prompt ---
# with open("./app/scripts/lwin_matching_prompt.txt", "r", encoding="utf-8") as f:
#     prompt = f.read()

# # --- Pydantic Models ---
# class MatchItem(BaseModel):
#     id: str
#     result: bool

# class MatchValidationResult(BaseModel):
#     matches: List[MatchItem]

# # --- Utility Functions ---
# def clean_json_nan(obj):
#     if isinstance(obj, dict):
#         return {k: clean_json_nan(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [clean_json_nan(i) for i in obj]
#     elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
#         return None
#     elif isinstance(obj, (np.integer, np.int64, np.int32)):
#         return int(obj)
#     elif isinstance(obj, (np.floating, np.float64, np.float32)):
#         return float(obj)
#     elif isinstance(obj, (date, datetime)):
#         return obj.isoformat()
#     return obj

# async def lwin_match_direct(payload, external_id, lwin_matching_service):
#     try:
#         params = LwinMatchingParams(
#             wine_name=payload.get('wine_name', ''),
#             lot_producer=payload.get('lot_producer', ''),
#             vintage=payload.get('vintage', ''),
#             region=payload.get('region', ''),
#             sub_region=payload.get('sub_region', ''),
#             country=payload.get('country', ''),
#             colour=payload.get('colour', '')
#         )

#         matched, lwin_code, match_score, match_item = await asyncio.to_thread(
#             lwin_matching_service.match, lwinMatchingParams=params, topk=1
#         )

#         for item in match_item:
#             item['id'] = int(item['id'])
#             item['lwin'] = int(item['lwin'])
#             item['date_added'] = item['date_added'].isoformat()
#             item['date_updated'] = item['date_updated'].isoformat()
#             item['reference'] = int(float(item['reference'])) if item.get('reference') else None

#         vintage = payload.get('vintage')
#         lwin_11_code = None
#         if lwin_code and vintage and len(vintage) == 4:
#             lwin_11_code = (
#                 [int(str(code) + vintage) for code in lwin_code]
#                 if isinstance(lwin_code, list) else int(str(lwin_code) + vintage)
#             )

#         return {
#             "external_id": external_id,
#             "matched": matched.value if hasattr(matched, 'value') else matched,
#             "lwin_code": lwin_code,
#             "lwin_11_code": lwin_11_code,
#             "match_score": match_score,
#             "match_item": match_item
#         }

#     except Exception as e:
#         print(f"[ERROR] Matching error for lot_item {external_id}: {e}")
#         return None

# def is_right_match(batch):
#     response = chatgpt.responses.parse(
#         model="gpt-4o",
#         input=[
#             {"role": "system", "content": prompt},
#             {"role": "user", "content": json.dumps(batch, ensure_ascii=False)}
#         ],
#         text_format=MatchValidationResult
#     )
#     return {item.id: item.result for item in response.output_parsed.matches}

# def batch_is_right_match(batch):
#     batch_size = 100
#     responses = {}
#     for i in range(0, len(batch), batch_size):
#         chunk = batch[i:i + batch_size]
#         responses.update(is_right_match(chunk))
#     return responses

# async def gather_lwin_matching_from_xls(xls_path: str, limit: int | None = None, lwin_service: LwinMatcherEngine | None = None):
#     entries = read_queries_from_excel(xls_path, limit=limit)

#     results = []
#     for i, e in enumerate(entries):
#         lot = {
#             "lot_name": e["lot_name"],
#             "lot_type": "Wine",
#             "lot_items": [
#                 {
#                     "id": f"xls-{i}",
#                     "vintage": e["vintage"],
#                     "colour": e["colour"],
#                     "lot_producer": ""
#                 }
#             ]
#         }

#         lot_result = {"lot": lot["lot_name"], "lot_items": []}
#         # 只有一个 lot_item，因此直接跑一个任务
#         payload = {
#             "wine_name": lot["lot_name"],
#             "vintage": e["vintage"],
#             "colour": e["colour"]
#         }
#         match_info = await lwin_match_direct(payload, lot["lot_items"][0]["id"], lwin_service)

#         if match_info and match_info.get("matched") == "exact_match":
#             m = match_info["match_item"][0]
#             lot_result["lot_items"].append({
#                 "id": str(m.get("id", "")),               # 用 LWIN 行 id 作为校验 key
#                 "lot_item": "",                            # 无来源 producer，留空即可
#                 "lot_type": lot.get("lot_type", ""),
#                 "match_result": {
#                     "matched_name": m.get("display_name", ""),
#                     "matched_producer": m.get("producer_title", ""),
#                     "matched_region": m.get("region", ""),
#                     "matched_sub_region": m.get("sub_region", "")
#                 }
#             })
#         else:
#             lot_result["lot_items"].append({
#                 "lot_item": "",
#                 "match_result": None
#             })

#         results.append(lot_result)

#     return results

# async def gather_lwin_matching_objects(sample_size, auction_house, lot_types, lwin_service):
#     sampled_lots = lots_client.sample_lots_with_lot_items(
#         sample_size=sample_size,
#         auction_house=auction_house,
#         filters=[("lot_type", "contains", lot_type) for lot_type in lot_types] 
#     )

#     results = []
#     for lot in sampled_lots:
#         if not lot.get("lot_items") or lot.get("lot_name", None) is None or lot.get("lot_type") == "spirits":
#             continue

#         lot_result = {"lot": lot.get("lot_name", ""), "lot_items": []}

#         tasks = [
#             lwin_match_direct({
#                 "wine_name": lot.get("lot_name", ""),
#                 # "lot_producer": item.get("lot_producer", ""),
#                 "vintage": item.get("vintage", ""),
#                 # "region": lot.get("region", ""),
#                 # "sub_region": lot.get("sub_region", ""),
#                 # "country": lot.get("country", ""),
#                 "colour": item.get("colour", "")
#             }, item.get("id"), lwin_service)
#             for item in lot.get("lot_items", [])
#         ]

#         match_results = await asyncio.gather(*tasks)

#         for match_info, lot_item in zip(match_results, lot.get("lot_items", [])):
#             if match_info and match_info.get("matched") == "exact_match":
#                 m = match_info["match_item"][0]
#                 lot_result["lot_items"].append({
#                     "id": str(m.get("id", "")),
#                     "lot_item": lot_item.get("lot_producer", ""),
#                     "lot_type": lot.get("lot_type", ""),
#                     "match_result": {
#                         "matched_name": m.get("display_name", ""),
#                         "matched_producer": m.get("producer_title", ""),
#                         "matched_region": m.get("region", ""),
#                         "matched_sub_region": m.get("sub_region", "")
#                     }
#                 })
#             else:
#                 lot_result["lot_items"].append({
#                     "lot_item": lot_item.get("lot_producer", ""),
#                     "match_result": None
#                 })

#         results.append(lot_result)
    
#     return results

# async def sample_and_match_lots(auction_house, lot_types, sample_size, xls_path: str | None = None):
#     lwin_service = LwinMatcherEngine(lwin_database_client.get_all())
#     if xls_path:
#         results = await gather_lwin_matching_from_xls(xls_path, lwin_service=lwin_service)
#     else:
#         initial_sample_size = sample_size
#         results = await gather_lwin_matching_objects(initial_sample_size, auction_house, lot_types, lwin_service)
#         while len(results) < initial_sample_size:
#             sample_size = initial_sample_size - len(results)
#             more_results = await gather_lwin_matching_objects(sample_size, auction_house, lot_types, lwin_service)
#             results.extend(more_results)
    
#     match_validations = batch_is_right_match(results)
#     null_count, match_correct, match_wrong, total_items = 0, 0, 0, 0

#     for result in results:
#         for item in result["lot_items"]:
#             total_items += 1
#             if item.get("match_result"):
#                 item["is_right_match"] = match_validations.get(item.get("id", ""), False)
#                 if item["is_right_match"]:
#                     match_correct += 1
#                 else:
#                     match_wrong += 1
#             else:
#                 item["is_right_match"] = False
#                 null_count += 1

#     output = {
#         "summary": {
#             "total_lots": len(results),
#             "total_items": total_items,
#             "matched_correct": match_correct,
#             "matched_correct_percentage": (match_correct / total_items) * 100 if total_items > 0 else 0,
#             "matched_wrong": match_wrong,
#             "matched_wrong_percentage": (match_wrong / total_items) * 100 if total_items > 0 else 0,
#             "no_match_result": null_count
#         },
#         "results": results
#     }

#     with open(f"Sample Match - {auction_house}.json", "w", encoding="utf-8") as f:
#         json.dump(clean_json_nan(output), f, ensure_ascii=False, indent=2)

#     return results

# if __name__ == "__main__":
#     auction_lot_types = {
#         "Sotheby's": ["Wine"],
#         "Christie's": ["Wine & Spirits"],
#         "Bonhams": ["Wine & Spirits", "Wine"],
#         "Zachys": ["Wine & Spirits"],
#     }

#     parser = argparse.ArgumentParser()
#     parser.add_argument('--auction_house', type=str, required=True, help='要匹配的 auction house 名称')
#     parser.add_argument('--count', type=int, required=True, help='Number of lots to sample')
#     parser.add_argument('--xls_path', type=str, required=False, help='Excel 文件路径（提供则从文件读取并替代 DB 抽样）')
#     args = parser.parse_args()

#     if args.xls_path:
#         asyncio.run(sample_and_match_lots(
#             auction_house=None, lot_types=[], sample_size=args.count, xls_path=args.xls_path
#         ))
#     else:
#         if not args.auction_house:
#             raise SystemExit("缺少 --auction_house 或 --xls_path 其一；未提供 --xls_path 时必须指定 --auction_house")
#         asyncio.run(sample_and_match_lots(
#             args.auction_house, auction_lot_types.get(args.auction_house, []), args.count
#         ))

import asyncio
import json
import math
import os
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from shared.database import LwinMatchingClient, LotsClient, LotItemsClient, LwinDatabaseClient
from lwin_matcher.app.model import LwinMatchingParams
from lwin_matcher.app.service.lwin_matching_engine import LwinMatcherEngine


class SampleMatcher:
    def __init__(
        self,
        prompt_path: str,
        auction_lot_types: Optional[Dict[str, List[str]]] = None,
    ):
        load_dotenv()

        self.lwin_client = LwinMatchingClient()
        self.lwin_database_client = LwinDatabaseClient()
        self.lots_client = LotsClient()
        self.lot_items_client = LotItemsClient()
        self.chatgpt = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt = f.read()

        self.lwin_service = LwinMatcherEngine(self.lwin_database_client.get_all())

        self.auction_lot_types = auction_lot_types or {
            "Sotheby's": ["Wine"],
            "Christie's": ["Wine & Spirits"],
            "Bonhams": ["Wine & Spirits", "Wine"],
            "Zachys": ["Wine & Spirits"],
        }

    @staticmethod
    def _clean_json_nan(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: SampleMatcher._clean_json_nan(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [SampleMatcher._clean_json_nan(i) for i in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return obj

    async def _lwin_match_direct(self, payload: Dict[str, Any], external_id: str) -> Optional[Dict[str, Any]]:
        try:
            params = LwinMatchingParams(
                wine_name=payload.get("wine_name", "") or "",
                lot_producer=payload.get("lot_producer", "") or "",
                vintage=payload.get("vintage", "") or "",
                region=payload.get("region", "") or "",
                sub_region=payload.get("sub_region", "") or "",
                country=payload.get("country", "") or "",
                colour=payload.get("colour", "") or "",
            )

            matched, lwin_code, match_score, match_item = await asyncio.to_thread(
                self.lwin_service.match, lwinMatchingParams=params, topk=1
            )

            for item in match_item:
                if "id" in item:
                    item["id"] = int(item["id"])
                if "lwin" in item:
                    item["lwin"] = int(item["lwin"])
                if item.get("date_added"):
                    item["date_added"] = item["date_added"].isoformat()
                if item.get("date_updated"):
                    item["date_updated"] = item["date_updated"].isoformat()
                if item.get("reference"):
                    item["reference"] = int(float(item["reference"]))

            return {
                "external_id": external_id,
                "matched": matched.value if hasattr(matched, "value") else matched,
                "lwin_code": lwin_code,
                "match_score": match_score,
                "match_item": match_item,
            }
        except Exception as e:
            print(f"[ERROR] Matching error for lot_item {external_id}: {e}")
            return None

    def _is_right_match_batch(self, batch: List[Dict[str, Any]]) -> Dict[str, bool]:
        BATCH_SIZE = 100
        results: Dict[str, bool] = {}

        for i in range(0, len(batch), BATCH_SIZE):
            chunk = batch[i : i + BATCH_SIZE]
            resp = self.chatgpt.responses.create(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": json.dumps(chunk, ensure_ascii=False)},
                ],
            )
            text = resp.output_text or "{}"
            try:
                parsed = json.loads(text)
                # 只合并 bool 值
                for k, v in parsed.items():
                    if isinstance(v, bool):
                        results[str(k)] = v
            except Exception as e:
                print("[WARN] AI 返回非 JSON，可忽略该片段：", e)
        return results

    @staticmethod
    def read_lotnames_from_xls(xls_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        df = pd.read_csv(xls_path)
        df = df[["lot_name"]].dropna()
        if limit:
            df = df.head(limit)

        entries = [{"row": int(i), "lot_name": str(n)} for i, n in df["lot_name"].items()]
        return entries

    async def gather_from_xls(self, xls_path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        rows = self.read_lotnames_from_xls(xls_path, limit=limit)

        results: List[Dict[str, Any]] = []
        for i, row in enumerate(rows):
            lot_name = row["lot_name"]
            lot_item_id = f"xls-{row['row']}"

            lot = {
                "lot": lot_name,
                "lot_items": [
                    {
                        "lot_item": None,
                        "lot_type": "Wine",
                    }
                ],
            }

            # 调 LWIN 匹配（只传 wine_name）
            match_info = await self._lwin_match_direct({"wine_name": lot_name}, lot_item_id)
            lot_entry = {"lot": lot_name, "lot_items": []}

            if match_info and match_info.get("matched") == "exact_match":
                m = match_info["match_item"][0]
                lot_entry["lot_items"].append(
                    {
                        "lot_item": None,
                        "match_result": {
                            "id": lot_item_id,
                            "matched_name": m.get("display_name", ""),
                            "matched_producer": m.get("producer_title", None),
                            "matched_region": m.get("region", ""),
                            "matched_sub_region": m.get("sub_region", ""),
                        },
                    }
                )
            else:
                lot_entry["lot_items"].append({"lot_item": None, "match_result": None})

            results.append(lot_entry)

        return results

    async def gather_from_db(self, auction_house: str, lot_types: List[str], sample_size: int) -> List[Dict[str, Any]]:
        sampled = self.lots_client.sample_lots_with_lot_items(
            sample_size=sample_size,
            auction_house=auction_house,
            filters=[("lot_type", "contains", lt) for lt in lot_types],
        )

        results: List[Dict[str, Any]] = []
        for lot in sampled:
            if not lot.get("lot_items") or not lot.get("lot_name") or lot.get("lot_type") == "spirits":
                continue

            lot_entry = {"lot": lot["lot_name"], "lot_items": []}

            tasks = []
            for item in lot.get("lot_items", []):
                lot_item_id = str(item.get("id"))
                payload = {
                    "wine_name": lot.get("lot_name", ""),
                    "vintage": item.get("vintage", ""),
                    "colour": item.get("colour", ""),
                }
                tasks.append(self._lwin_match_direct(payload, lot_item_id))

            match_results = await asyncio.gather(*tasks)

            for match_info, lot_item in zip(match_results, lot.get("lot_items", [])):
                if match_info and match_info.get("matched") == "exact_match":
                    m = match_info["match_item"][0]
                    lot_entry["lot_items"].append(
                        {
                            "lot_item": lot_item.get("lot_producer", ""),
                            "lot_type": lot.get("lot_type", ""),
                            "match_result": {
                                "id": str(lot_item.get("id")),  # 放在 match_result.id
                                "matched_name": m.get("display_name", ""),
                                "matched_producer": m.get("producer_title", None),
                                "matched_region": m.get("region", ""),
                                "matched_sub_region": m.get("sub_region", ""),
                            },
                        }
                    )
                else:
                    lot_entry["lot_items"].append(
                        {"lot_item": lot_item.get("lot_producer", ""), "match_result": None}
                    )

            results.append(lot_entry)

        return results

    async def run(
        self,
        auction_house: Optional[str],
        sample_size: int,
        xls_path: Optional[str] = None,
        limit: Optional[int] = None,
        out_name: Optional[str] = None,
        validate: bool = False,
    ) -> List[Dict[str, Any]]:

        if xls_path:
            results = await self.gather_from_xls(xls_path, limit=limit)
            out_file = out_name or f"Sample Match - XLS.json"
        else:
            if not auction_house:
                raise ValueError("未提供 auction_house（从 DB 抽样时必需）")
            lot_types = self.auction_lot_types.get(auction_house, [])
            results = await self.gather_from_db(auction_house, lot_types, sample_size)
            out_file = out_name or f"Sample Match - {auction_house}.json"

        if validate:
            validations = self._is_right_match_batch(results)

        null_count = match_correct = match_wrong = total_items = 0
        for lot in results:
            for it in lot["lot_items"]:
                total_items += 1
                mr = it.get("match_result")
                if mr:
                    lot_item_id = str(mr.get("id"))
                    if validate:
                        it["is_right_match"] = bool(validations.get(lot_item_id, False))
                        if it["is_right_match"]:
                            match_correct += 1
                        else:
                            match_wrong += 1
                else:
                    it["is_right_match"] = False
                    null_count += 1

        output = {
            "summary": {
                "total_lots": len(results),
                "total_items": total_items,
                "matched_correct": match_correct,
                "matched_correct_percentage": (match_correct / total_items) * 100 if total_items else 0,
                "matched_wrong": match_wrong,
                "matched_wrong_percentage": (match_wrong / total_items) * 100 if total_items else 0,
                "no_match_result": null_count,
            },
            "results": results,
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(self._clean_json_nan(output), f, ensure_ascii=False, indent=2)

        return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--auction_house", type=str, required=False, help="要匹配的 auction house 名称（从 DB 抽样时必填）")
    parser.add_argument("--count", type=int, required=False, default=1, help="抽样数量（DB 模式）")
    parser.add_argument("--xls_path", type=str, required=False, help="Excel 文件路径（仅列 lot_name）")
    parser.add_argument("--limit", type=int, required=False, help="XLS 只取前 N 条")
    parser.add_argument("--validate", action="store_true", help="是否进行 AI 校验")
    args = parser.parse_args()

    matcher = SampleMatcher(prompt_path="./lwin_matching_prompt.txt")

    if args.xls_path:
        asyncio.run(matcher.run(auction_house=None, sample_size=0, xls_path=args.xls_path, limit=args.limit, validate=args.validate))
    else:
        if not args.auction_house:
            raise SystemExit("未提供 --auction_house 或 --xls_path 其一；未提供 --xls_path 时必须指定 --auction_house")
        asyncio.run(matcher.run(auction_house=args.auction_house, sample_size=args.count, validate=args.validate))
