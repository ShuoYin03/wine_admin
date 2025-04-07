import sys
import json
sys.path.append('../..')
from flask import Blueprint, request, Response
from database.database_client import DatabaseClient
from app.utils import serialize_for_json, justify_ops

lwin_query_blueprint = Blueprint('lwin_query', __name__)
db = DatabaseClient()
    
@lwin_query_blueprint.route('/lwin_query', methods=['POST'])
async def lwin_query_not_match():
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
            results, count = db.query_items(
                table_name='lwin_matching',
                filters=filters,
                order_by=order_by,
                limit=page_size,
                offset=offset,
                select_fields=select_fields,
                distinct_fields=distinct_fields,
                return_count=True
            )
            results = serialize_for_json(results)
            return Response(json.dumps({"data": results, "count": count}), mimetype='application/json')

        results = db.query_items(
            table_name='lwin_matching',
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            select_fields=select_fields,
            distinct_fields=distinct_fields,
        )
        results = serialize_for_json(results)
        return Response(json.dumps({"data": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@lwin_query_blueprint.route('/lwin_and_lots_query', methods=['POST'])
async def lwin_query_all():
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
            results, count = db.query_lwin_with_lots(
                filters=filters,
                order_by=order_by,
                limit=page_size,
                offset=offset,
                select_fields=select_fields,
                distinct_fields=distinct_fields,
                return_count=True
            )
            results = serialize_for_json(results)
            return Response(json.dumps({"data": results, "count": count}), mimetype='application/json')

        results = db.query_lwin_with_lots(
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            select_fields=select_fields,
            distinct_fields=distinct_fields,
        )
        results = serialize_for_json(results)
        return Response(json.dumps({"data": results}), mimetype='application/json')

    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)