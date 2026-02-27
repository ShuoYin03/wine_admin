import json
from app.utils import serialize_for_json, justify_ops
from flask import Blueprint, request, Response, current_app

auction_query_blueprint = Blueprint('auction_query', __name__)

@auction_query_blueprint.route('/auction', methods=['GET'])
async def auction():
    try:
        auction_id = request.args.get('auction_id')
        results = current_app.auctions_client.query_single_auction(auction_id)
        results = serialize_for_json(results)
        return Response(json.dumps({"auction": results}), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@auction_query_blueprint.route('/auction_query_with_sales', methods=['POST'])
async def auction_query_with_sales():
    try:
        payload = request.get_json() or {}
        filters = payload.get('filters', [])
        filters = justify_ops(filters)
        order_by = payload.get('order_by')
        page = int(payload.get('page', 1))
        page_size = int(payload.get('page_size', 30))
        return_count = payload.get('return_count', False)
        offset = (page - 1) * page_size

        results, count = current_app.auctions_client.query_auctions_with_sales(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            return_count=True
        )

        results = serialize_for_json(results)

        if return_count:
            return Response(json.dumps({"auctions": results, "count": count}), mimetype='application/json')
        
        return Response(json.dumps({"auctions": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)