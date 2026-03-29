import json
from app.service import CsvExportService
from app.utils import serialize_for_json, parse_query_payload, json_response
from flask import Blueprint, request, Response, current_app

lot_query_blueprint = Blueprint('lot_query', __name__)

@lot_query_blueprint.route('/lot_query', methods=['POST'])
async def query():
    try:
        q = parse_query_payload()

        results, count = current_app.lots_client.query_lots_with_items_and_auction(
            filters=q.filters,
            order_by=q.order_by,
            limit=q.page_size,
            offset=q.offset,
            return_count=True
        )

        results = serialize_for_json(results)
        return json_response(results, count=count)

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

@lot_query_blueprint.route('/auction/<auction_id>/lots', methods=['POST'])
async def auction_lots_query(auction_id: str) -> Response:
    try:
        q = parse_query_payload()
        filters = [{
            "field": "auction_id",
            "op": "=",
            "value": auction_id
        }] + q.filters

        results, count = current_app.lots_client.query_lots_with_items_and_auction(
            filters=filters,
            order_by=q.order_by,
            limit=q.page_size,
            offset=q.offset,
            return_count=True,
        )

        return json_response(serialize_for_json(results), count=count)

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


@lot_query_blueprint.route('/lot_export_csv', methods=['POST'])
async def lot_export_csv():
    try:
        q = parse_query_payload()

        results = current_app.lots_client.query_lots_with_items_and_auction(
            filters=q.filters,
            order_by=q.order_by
        )
        return CsvExportService.to_response(serialize_for_json(results), filename="lots.csv")

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)