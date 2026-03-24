import json
from app.service import CsvExportService
from app.utils import serialize_for_json, justify_ops
from flask import Blueprint, request, Response, current_app

lot_query_blueprint = Blueprint('lot_query', __name__)

@lot_query_blueprint.route('/lot_query', methods=['POST'])
async def query():
    try:
        payload = request.get_json() or {}
        filters = payload.get('filters', [])
        filters = justify_ops(filters)
        order_by = payload.get('order_by')
        page = int(payload.get('page', 1))
        page_size = int(payload.get('page_size', 30))
        return_count = payload.get('return_count', False)
        offset = (page - 1) * page_size

        results, count = current_app.lots_client.query_lots_with_items_and_auction(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            return_count=True
        )

        results = serialize_for_json(results)

        if return_count:
            return Response(json.dumps({"lots": results, "count": count}), mimetype='application/json')
        
        return Response(json.dumps({"lots": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

@lot_query_blueprint.route('/auction/<auction_id>/lots', methods=['POST'])
async def auction_lots_query(auction_id: str) -> Response:
    try:
        payload = request.get_json() or {}
        extra_filters: list = justify_ops(payload.get('filters', []))
        order_by = payload.get('order_by')
        page = int(payload.get('page', 1))
        page_size = int(payload.get('page_size', 30))
        return_count: bool = payload.get('return_count', False)
        offset = (page - 1) * page_size

        filters = [["auction_id", "=", auction_id]] + extra_filters

        results, count = current_app.lots_client.query_lots_with_items_and_auction(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            return_count=True,
        )

        body: dict = {"lots": serialize_for_json(results)}
        if return_count:
            body["count"] = count

        return Response(json.dumps(body), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


@lot_query_blueprint.route('/lot_export_csv', methods=['POST'])
async def lot_export_csv():
    try:
        payload = request.get_json() or {}
        filters = justify_ops(payload.get('filters', []))
        order_by = payload.get('order_by')

        results = current_app.lots_client.query_lots_with_items_and_auction(
            filters=filters,
            order_by=order_by
        )
        return CsvExportService.to_response(serialize_for_json(results), filename="lots.csv")

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)