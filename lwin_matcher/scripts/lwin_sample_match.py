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

from shared.database.lwin_matching_client import LwinMatchingClient
from shared.database.lots_client import LotsClient
from shared.database.lot_items_client import LotItemsClient
from shared.database.lwin_database_client import LwinDatabaseClient
from app.models.lwin_matching_params import LwinMatchingParams
from app.service.lwin_matching_engine import LwinMatcherEngine

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
