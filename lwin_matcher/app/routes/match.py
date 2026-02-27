import json
import logging
import asyncio
import numpy as np
import pandas as pd
from flask import current_app, Blueprint, request, Response
from app.models.lwin_matching_params import LwinMatchingParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

match_blueprint = Blueprint('match', __name__)

@match_blueprint.route('/match', methods=['POST'])
async def match():
    payload = request.get_json()

    vintage = payload.get('vintage', None)
    topk = payload.get('topk', 1)
    lwin_matching_params = LwinMatchingParams(
        wine_name=payload.get('wine_name', ''),
        lot_producer=payload.get('lot_producer', ''),
        vintage=payload.get('vintage', ''),
        region=payload.get('region', ''),
        sub_region=payload.get('sub_region', ''),
        country=payload.get('country', ''),
        colour=payload.get('colour', '')
    )

    try:
        matched, lwin_code, match_score, match_item = await asyncio.to_thread(
            current_app.lwin_matching_engine.match, lwin_matching_params, topk=topk
        )

        for item in match_item:
            item['id'] = int(item['id']) if isinstance(item['id'], np.int64) else item['id']
            item['lwin'] = int(item['lwin']) if isinstance(item['lwin'], np.int64) else item['lwin']
            item['date_added'] = item['date_added'].isoformat() if isinstance(item['date_added'], pd.Timestamp) else item['date_added']
            item['date_updated'] = item['date_updated'].isoformat() if isinstance(item['date_updated'], pd.Timestamp) else item['date_updated']
            item['reference'] = int(float(item['reference'])) if 'reference' in item and item['reference'] else None

        lwin_11_code = None
        if lwin_code and vintage and isinstance(vintage, str) and len(vintage) == 4:
            if isinstance(lwin_code, list):
                lwin_11_code = [int(str(code) + vintage) for code in lwin_code]
            else:
                lwin_11_code = int(str(lwin_code) + vintage)

        result = {
            "matched": matched.value,
            "lwin_code": to_native(lwin_code),
            "lwin_11_code": lwin_11_code,
            "match_score": match_score,
            "match_item": match_item
        }

        return Response(json.dumps(result), mimetype='application/json')
    except Exception as e:
        print(f"[ERROR] /match encountered an exception: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=400)
    

@match_blueprint.route('/match_target', methods=['POST'])
async def match_target():
    payload = request.get_json() or {}
    target_name = payload.get('target_name', '')

    lwin_matching_params = LwinMatchingParams(
        wine_name=payload.get('wine_name', ''),
        lot_producer=payload.get('lot_producer', ''),
        vintage=payload.get('vintage', ''),
        region=payload.get('region', ''),
        sub_region=payload.get('sub_region', ''),
        country=payload.get('country', ''),
        colour=payload.get('colour', '')
    )

    try:
        if not target_name:
            return Response(
                json.dumps({"error": "target_name is required"}),
                mimetype='application/json',
                status=400
            )

        candidates = current_app.lwin_database_client.get_by_display_name(target_name)
        if not candidates:
            return Response(
                json.dumps({"error": f"No record found in lwin_database for target_name='{target_name}'"}),
                mimetype='application/json',
                status=400
            )

        if len(candidates) > 1:
            return Response(
                json.dumps({"error": f"Multiple records found for target_name='{target_name}', please make display_name unique"}),
                mimetype='application/json',
                status=400
            )

        target_idx = int(candidates[0]['id'])

        match_score = await asyncio.to_thread(
            current_app.lwin_matching_engine.match_target_by_id, lwin_matching_params, target_idx
        )

        result = {
            "match_score": float(match_score),
            "target_idx": target_idx,
        }

        return Response(json.dumps(result), mimetype='application/json')
    except Exception as e:
        print(f"[ERROR] /match encountered an exception: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=400)

def to_native(x):
    if isinstance(x, np.integer): return int(x)
    if isinstance(x, pd.Timestamp): return x.isoformat()
    if isinstance(x, list): return [to_native(i) for i in x]
    return x