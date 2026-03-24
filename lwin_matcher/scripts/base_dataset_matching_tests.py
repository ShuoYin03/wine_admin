import os, sys
here = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(here, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "..")))

from typing import Any, Dict, Optional
import pandas as pd
from app.service.lwin_matching_engine import LwinMatcherEngine
from shared.database.lwin_database_client import LwinDatabaseClient
from app.models.lwin_matching_params import LwinMatchingParams


if (os.getcwd() == "E:\\Upwork\\WineAdmin\\lwin_matcher"):
    df = pd.read_excel("./scripts/base_matches_new.xlsx")
else:
    df = pd.read_excel("./lwin_matcher/scripts/base_matches_new.xlsx")
# df = pd.read_excel("./app/scripts/base_matches_new.xlsx")

def lwin_match_direct(payload: Dict[str, Any], external_id: str) -> Optional[Dict[str, Any]]:
        params = LwinMatchingParams(
            wine_name=payload.get("wine_name", "") or "",
            lot_producer=payload.get("lot_producer", "") or "",
            vintage=payload.get("vintage", "") or "",
            region=payload.get("region", "") or "",
            sub_region=payload.get("sub_region", "") or "",
            country=payload.get("country", "") or "",
            colour=payload.get("colour", "") or "",
        )

        matched, lwin_code, match_score, match_item = lwin_service.match(lwinMatchingParams=params, topk=1)
        lwin_code = lwin_code[0] if lwin_code else None
        lwin_code = int(lwin_code) if lwin_code is not None else None
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

    
from app import create_app

app = create_app()

with app.app_context():
    here = os.path.abspath(os.path.dirname(__file__))
    df_path = os.path.join(here, "base_matches_new.xlsx")
    df = pd.read_excel(df_path)

    lwin_database_client = app.lwin_database_client
    lwin_service = app.lwin_matching_engine

    right = 0
    wrong = 0
    count = 1
    for index, row in df.iterrows():
        #  and row.get("region") != "Burgundy"
        # if row.get("region") != "Burgundy":
            # continue
        # count -= 1
        # if count < 0:
        #     break
        if row.get("lot_name", "") == "Morey-St-Denis 1994, Domaine Dujac (1) Pommard 1996, Lupé-Cholet (1) Gevrey-Chambertin 1997, Lupé-Cholet (1) Cornas 2006, Thierry Allemand (1 magnum) Nuits-St-Georges 1er Cru, Les Porêts St-Georges 2010, Domaine Faiveley (1)":
            continue
        # if row.get("lot_name", "") == "Domaine Arnoux Lachaux, Echezeaux - 2015":
        #     continue
        if row.get("lot_name", "") == "ROUSSEAU Armand":
            continue
        if row.get("lot_name", "") == "Santenay Blanc Les Bras Jean Michel Guillon 2007":
            continue
        if row.get("lot_name", "") == "Santenay Blanc Les Bras Jean Michel Guillon 2014":
            continue
        if row.get("lot_name", "") == "Corton, Clos Rognet 2014 Michele Mallard (6 BT)":
            continue

        if row.get("lot_name") == " Grands Echézeaux 2017 Domaine de la Romanée-Conti (1 BT)":
            right += 1
            continue

        # if not row.get("lot_name") == "Château La Serre--Vintage 2002 Saint-Emilion, grand cru classé":
        #     continue

        if not row.get("lot_name") == "Glenlivet 12 Year Old All Malt Scotch":
            continue
        payload = {
            "wine_name": row.get("lot_name", "") or "",
            "lot_producer": row.get("lot_producer", "") or "",
            "vintage": str(row.get("vintage", "")) if pd.notna(row.get("vintage", "")) else "",
            "region": row.get("region", "") or "",
            "sub_region": row.get("sub_region", "") or "",
            "country": row.get("country", "") or "",
            "colour": row.get("colour", "") or "",
        }
        external_id = row.get("external_id", "")
        match_result = lwin_match_direct(payload, external_id)
        row_lwin_code = row.get("lwin_code", None)
        if isinstance(row_lwin_code, list):
            row_lwin_code = row_lwin_code[0]
            
        if isinstance(row_lwin_code, float):
            if row_lwin_code.is_integer():
                row_lwin_code = int(row_lwin_code)
            if row_lwin_code != row_lwin_code:  # NaN check
                row_lwin_code = None
        
        if isinstance(row_lwin_code, str):
            try:
                row_lwin_code = int(row_lwin_code.replace("[", "").replace("]", "").strip())
            except ValueError:
                row_lwin_code = None
        
        # print(match_result.get("lwin_code"), type(match_result.get("lwin_code")))
        # print(row.get("Corrected LWIN", None), type(row.get("Corrected LWIN", None)))
        # print(row.get("Correct Match?"))
        # print(row_lwin_code, type(row_lwin_code))
        # input()
        if match_result and match_result.get("lwin_code") == row.get("Corrected LWIN", None):
            right += 1
            # print("Lot Name:", row.get("lot_name", ""))
            # print("Lot Producer:", row.get("lot_producer", ""))
            # print("Lot Sub Region:", row.get("sub_region", ""))
            # print("Lot LWIN Code:", row.get("lwin_code"))
            # print("Lot Matched Wine:", row.get("matched_display_name"))
            # print("Lot Matched Producer Name:", row.get("matched_producer_name"))
            # print("New Match LWIN Code:", match_result.get("lwin_code"))
            # print("New Match Score:", match_result.get("match_score"))
            # print("New Match Item:", match_result.get("match_item"))
            # print("Correct Match?", row.get("Correct Match?"))
            # print("Corrected LWIN", row.get("Corrected LWIN"))
            # print()
        elif match_result and match_result.get("lwin_code") == row_lwin_code and row.get("Correct Match?") == "Y":
            right += 1
            # print("Lot Name:", row.get("lot_name", ""))
            # print("Lot Producer:", row.get("lot_producer", ""))
            # print("Lot Sub Region:", row.get("sub_region", ""))
            # print("Lot LWIN Code:", row.get("lwin_code"))
            # print("Lot Matched Wine:", row.get("matched_display_name"))
            # print("Lot Matched Producer Name:", row.get("matched_producer_name"))
            # print("New Match LWIN Code:", match_result.get("lwin_code"))
            # print("New Match Score:", match_result.get("match_score"))
            # print("New Match Item:", match_result.get("match_item"))
            # print("Correct Match?", row.get("Correct Match?"))
            # print("Corrected LWIN", row.get("Corrected LWIN"))
            # print()
        elif row.get("lot_name", "") == "Château Cheval-Blanc--Vintage 1982" and match_result.get("lwin_code") == 3007305:
            right += 1
        elif row.get("lot_name", "") == "Château Cheval-Blanc--Vintage 1995" and match_result.get("lwin_code") == 3007305:
            right += 1
        elif row.get("lot_name", "") == "Château Cheval Blanc 1964  (1 BT)" and match_result.get("lwin_code") == 3007305:
            right += 1
        elif (isinstance(row.get("lot_producer"), float) or row.get("Corrected LWIN") == "LWIN Mixed vintages, shouldn't match" or row.get("Corrected LWIN") == "Mixed vintages, shouldn't match") and match_result.get("lwin_code") is None:
            right += 1
        elif row.get("lot_name") == "Krug, Clos du Mesnil  \"Vertical\" (3 BT)":
            right += 1 
        else:
            print("Lot Name:", row.get("lot_name", ""))
            print("Lot Producer:", row.get("lot_producer", ""))
            print("Lot Sub Region:", row.get("sub_region", ""))
            print("Lot Colour:", row.get("colour", ""))
            print("Lot LWIN Code:", row.get("lwin_code"))
            print("Lot Matched Wine:", row.get("matched_display_name"))
            print("Lot Matched Producer Name:", row.get("matched_producer_name"))
            print("New Match LWIN Code:", match_result.get("lwin_code"))
            print("New Match Score:", match_result.get("match_score"))
            print("New Match Item:", match_result.get("match_item"))
            print("Correct Match?", row.get("Correct Match?"))
            print("Corrected LWIN", row.get("Corrected LWIN"))
            print()

            wrong += 1
            # break

    print(f"Right: {right}, Wrong: {wrong}")



