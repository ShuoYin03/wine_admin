import sys
import json
sys.path.append('../..')
from flask import Blueprint, request, Response
from database.database_client import DatabaseClient

lwin_query_blueprint = Blueprint('lwin_query', __name__)
db = DatabaseClient()

@lwin_query_blueprint.route('/lwin_query_all', methods=['GET'])
async def lwin_query_all():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lwin_matching', offset=page*page_size, limit=page_size)
        return Response(json.dumps(results), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

@lwin_query_blueprint.route('/lwin_query_exact_match', methods=['POST'])
async def lwin_query_exact_match():
    payload = request.get_json()
    filters = {**payload.get('filters', {}), **{"matched": "exact_match"}}
    order_by = payload.get('order_by', {})
    page = int(payload.get('page', 1))
    page_size = int(payload.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lwin_matching', filters=filters, order_by=order_by, limit=page_size, offset=page*page_size)
        return Response(json.dumps(results), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@lwin_query_blueprint.route('/lwin_query_multi_match', methods=['POST'])
async def lwin_query_multi_match():
    payload = request.get_json()
    filters = {**payload.get('filters', {}), **{"matched": "multi_match"}}
    order_by = payload.get('order_by')
    page = int(payload.get('page', 1))
    page_size = int(payload.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lwin_matching', filters=filters, order_by=order_by, limit=page_size, offset=page*page_size)
        return Response(json.dumps(results), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
    
@lwin_query_blueprint.route('/lwin_query_not_match', methods=['POST'])
async def lwin_query_not_match():
    payload = request.get_json()
    filters = {**payload.get('filters', {}), **{"matched": "not_match"}}
    order_by = payload.get('order_by')
    page = int(payload.get('page', 1))
    page_size = int(payload.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lwin_matching', filters=filters, order_by=order_by, limit=page_size, offset=page*page_size)
        return Response(json.dumps(results), mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)