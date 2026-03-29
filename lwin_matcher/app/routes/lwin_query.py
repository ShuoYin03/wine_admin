import json
from flask import Blueprint, request, Response, current_app
from app.utils import serialize_for_json, parse_query_payload, json_response

lwin_query_blueprint = Blueprint('lwin_query', __name__)

@lwin_query_blueprint.route('/lwin_query', methods=['POST'])
async def lwin_query():
    try:
        q = parse_query_payload()

        results, count = current_app.lwin_matching_client.query_lwin_with_lot_items(
            filters=q.filters,
            order_by=q.order_by,
            limit=q.page_size,
            offset=q.offset,
            return_count=q.return_count
        )

        return json_response(serialize_for_json(results), count=count)

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@lwin_query_blueprint.route('/lwin_count', methods=['GET'])
async def lwin_query_count():
    try:
        exact_match_count = current_app.lwin_matching_client.query_exact_match_count()
        multi_match_count = current_app.lwin_matching_client.query_multi_match_count()
        not_match_count = current_app.lwin_matching_client.query_not_match_count()

        payload = {
            "exact_match_count": exact_match_count,
            "multi_match_count": multi_match_count,
            "not_match_count": not_match_count
        }

        return json_response(payload)
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)