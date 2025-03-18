import sys
sys.path.append('../..')
from app.model import LwinMatchingParams
from ..service import LwinMatchingService
from flask import Blueprint, jsonify, request

match_blueprint = Blueprint('match', __name__)
lwin_matching_service = LwinMatchingService()

@match_blueprint.route('/match', methods=['POST'])
def match():
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
        lot_producer=lot_producer,
        vintage=vintage,
        region=region,
        sub_region=sub_region,
        country=country,
        colour=colour
    )

    try:
        matched, lwin_code, match_score, match_item = lwin_matching_service.lwin_matching(lwin_matching_params)
        print(matched.value, lwin_code, match_score, match_item)
        result = {
            "matched": matched.value,
            "lwin_code": lwin_code,
            "match_score": match_score,
            "match_item": match_item
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500