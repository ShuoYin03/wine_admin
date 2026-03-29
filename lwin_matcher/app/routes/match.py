import json
import logging
import asyncio
from flask import current_app, Blueprint, request, Response
from app.models.lwin_matching_params import LwinMatchingParams
from app.utils.build_response import json_response

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

        lwin_11_code = None
        if lwin_code and vintage and isinstance(vintage, str) and len(vintage) == 4:
            if isinstance(lwin_code, list):
                lwin_11_code = [int(str(code) + vintage) for code in lwin_code]
            else:
                lwin_11_code = int(str(lwin_code) + vintage)

        result = {
            "matched": matched.value,
            "lwin_code": lwin_code,
            "lwin_11_code": lwin_11_code,
            "match_score": match_score,
            "match_item": match_item
        }

        return json_response(result)
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

        return json_response(result)
    except Exception as e:
        print(f"[ERROR] /match encountered an exception: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=400)

