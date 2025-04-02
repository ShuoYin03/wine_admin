import sys
import json
sys.path.append('../..')
from app.utils import serialize_for_json
from flask import Blueprint, request, Response
from database.database_client import DatabaseClient

query_blueprint = Blueprint('query', __name__)
db = DatabaseClient()

@query_blueprint.route('/query_all', methods=['GET'])
async def query_all():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lots', offset=page*page_size, limit=page_size)
        return Response(json.dumps(results), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@query_blueprint.route('/query', methods=['POST'])
async def query():
    payload = request.get_json()
    filters = payload.get('filters')
    order_by = payload.get('order_by')
    page = int(payload.get('page', 1))
    page_size = int(payload.get('page_size', 30))
    return_count = payload.get('return_count', False)
    offset = (page - 1) * page_size if payload.get('page') != None else None
    
    try:
        if return_count:
            results, count = db.query_lots_with_auction(filters=filters, order_by=order_by, limit=page_size, offset=offset, return_count=return_count)
            results = serialize_for_json(results)
            return Response(json.dumps({"lots": results, "count": count}), mimetype='application/json')
        
        results = db.query_lots_with_auction(filters=filters, order_by=order_by, limit=page_size, offset=offset)
        results = serialize_for_json(results)
        return Response(json.dumps({"lots": results}), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)