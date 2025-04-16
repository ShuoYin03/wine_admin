import sys
import json
import asyncio
import pandas as pd
import numpy as np
sys.path.append('../..')
from app.model import LwinMatchingParams
from ..service import LwinMatchingService
from flask import Blueprint, request, Response

match_blueprint = Blueprint('match', __name__)
lwin_matching_service = LwinMatchingService()

@match_blueprint.route('/match', methods=['POST'])
async def match():
    payload = request.get_json()
    wine_name = payload.get('wine_name', '')
    lot_producer = payload.get('lot_producer', '')
    vintage = payload.get('vintage', '')
    region = payload.get('region', '')
    sub_region = payload.get('sub_region', '')
    country = payload.get('country', '')
    colour = payload.get('colour', '')

    lwin_matching_params = LwinMatchingParams(
        wine_name=wine_name,
        lot_producer=lot_producer[0] if type(lot_producer) == list else lot_producer,
        vintage=vintage,
        region=region,
        sub_region=sub_region,
        country=country,
        colour=colour
    )

    try:
        matched, lwin_code, match_score, match_item = await asyncio.to_thread(
            lwin_matching_service.lwin_matching, lwin_matching_params
        )

        for item in match_item:
            item['id'] = int(item['id']) if isinstance(item['id'], np.int64) else item['id']
            item['date_added'] = item['date_added'].isoformat() if isinstance(item['date_added'], pd.Timestamp) else item['date_added']
            item['date_updated'] = item['date_updated'].isoformat() if isinstance(item['date_updated'], pd.Timestamp) else item['date_updated']

        lwin_11_code = None
        if lwin_code and vintage and isinstance(vintage, str) and len(vintage) == 4:
            if isinstance(lwin_code, list):
                lwin_11_code = [code + vintage for code in lwin_code]
            else:
                lwin_11_code = lwin_code + vintage

        result = {
            "matched": matched.value,
            "lwin_code": lwin_code,
            "lwin_11_code": lwin_11_code,
            "match_score": match_score,
            "match_item": match_item
        }

        return Response(json.dumps(result), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=400)
    
@match_blueprint.route('/test_match', methods=['POST'])
async def test_match():
    payload = request.get_json()
    wine_name = payload.get('wine_name', '')
    lot_producer = payload.get('lot_producer', '')
    vintage = payload.get('vintage', '')
    region = payload.get('region', '')
    sub_region = payload.get('sub_region', '')
    country = payload.get('country', '')
    colour = payload.get('colour', '')

    target_record = payload.get('target_record', {})
    if not target_record:
        return Response(json.dumps({"error": "A target record is required"}), mimetype='application/json', status=400)

    
    lwin_matching_params = LwinMatchingParams(
        wine_name=wine_name,
        lot_producer=lot_producer[0] if type(lot_producer) == list else lot_producer,
        vintage=vintage,
        region=region,
        sub_region=sub_region,
        country=country,
        colour=colour
    )

    try:
        matched, lwin_code, match_score, match_item = await asyncio.to_thread(
            lwin_matching_service.lwin_matching, lwin_matching_params
        )

        for item in match_item:
            item['id'] = int(item['id']) if isinstance(item['id'], np.int64) else item['id']
            item['date_added'] = item['date_added'].isoformat() if isinstance(item['date_added'], pd.Timestamp) else item['date_added']
            item['date_updated'] = item['date_updated'].isoformat() if isinstance(item['date_updated'], pd.Timestamp) else item['date_updated']

        lwin_11_code = None
        if lwin_code and vintage and isinstance(vintage, str) and len(vintage) == 4:
            if isinstance(lwin_code, list):
                lwin_11_code = [code + vintage for code in lwin_code]
            else:
                lwin_11_code = lwin_code + vintage

        result = {
            "matched": matched.value,
            "lwin_code": lwin_code,
            "lwin_11_code": lwin_11_code,
            "match_score": match_score,
            "match_item": match_item
        }

        return Response(json.dumps(result), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=400)