import sys
import json
sys.path.append('../..')
from flask import Blueprint, request, Response, current_app
from app.utils import serialize_for_json, justify_ops

lwin_query_blueprint = Blueprint('lwin_query', __name__)

@lwin_query_blueprint.route('/lwin_query', methods=['POST'])
async def lwin_query():
    try:
        payload = request.get_json() or {}
        filters = payload.get('filters', [])
        filters = justify_ops(filters)
        order_by = payload.get('order_by')
        page = int(payload.get('page', 1))
        page_size = int(payload.get('page_size', 30))
        return_count = payload.get('return_count', False)
        offset = (page - 1) * page_size

        results, count = current_app.lwin_matching_client.query_lwin_with_lots(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            return_count=return_count
        )

        results = serialize_for_json(results)
        if return_count:
            return Response(json.dumps({"data": results, "count": count}), mimetype='application/json')
        return Response(json.dumps({"data": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@lwin_query_blueprint.route('/lwin_query_count', methods=['GET'])
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

        return Response(json.dumps({"data": payload}), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)