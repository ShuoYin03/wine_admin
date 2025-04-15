import io
import csv
import sys
import json
sys.path.append('../..')
from flask import Blueprint, request, Response
from database.database_client import DatabaseClient
from app.utils import serialize_for_json, justify_ops

lot_query_blueprint = Blueprint('lot_query', __name__)
db = DatabaseClient()

@lot_query_blueprint.route('/lot_query', methods=['POST'])
async def query():
    try:
        payload = request.get_json() or {}
        filters = payload.get('filters', [])
        filters = justify_ops(filters)
        order_by = payload.get('order_by')
        page = int(payload.get('page', 1))
        page_size = int(payload.get('page_size', 30))
        select_fields = payload.get('select_fields', None)
        distinct_fields = payload.get('distinct_fields', None)
        return_count = payload.get('return_count', False)
        offset = (page - 1) * page_size
        if distinct_fields:
            page = None
            page_size = None
            offset = None

        if return_count:
            results, count = db.query_lots_with_auction(
                filters=filters,
                order_by=order_by,
                limit=page_size,
                offset=offset,
                select_fields=select_fields,
                distinct_fields=distinct_fields,
                return_count=True
            )
            results = serialize_for_json(results)
            return Response(json.dumps({"lots": results, "count": count}), mimetype='application/json')

        results = db.query_lots_with_auction(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            select_fields=select_fields,
            distinct_fields=distinct_fields,
        )
        results = serialize_for_json(results)
        return Response(json.dumps({"lots": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    

@lot_query_blueprint.route('/lot_export_csv', methods=['POST'])
async def lot_export_csv():
    try:
        payload = request.get_json() or {}
        filters = payload.get('filters', [])
        filters = justify_ops(filters)
        order_by = payload.get('order_by')

        results = db.query_lots_with_auction(
            filters=filters,
            order_by=order_by
        )
        results = serialize_for_json(results)

        output = io.StringIO()
        writer = csv.writer(output)

        if results:
            writer.writerow(results[0].keys())
            for lot in results:
                writer.writerow(lot.values())
        else:
            writer.writerow(["No Data"])

        csv_bytes = output.getvalue().encode("utf-8-sig")
        output.close()

        response = Response(csv_bytes, mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=lots.csv'

        return response
        
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)