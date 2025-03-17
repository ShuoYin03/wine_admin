import sys
sys.path.append('../..')
from flask import Blueprint, jsonify, request
from database.database_client import DatabaseClient

query_blueprint = Blueprint('query', __name__)
db = DatabaseClient()

@query_blueprint.route('/query_all', methods=['GET'])
def query_all():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lots', offset=page*page_size, limit=page_size)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@query_blueprint.route('/query', methods=['POST'])
def query():
    payload = request.get_json()
    filters = payload.get('filters')
    order_by = payload.get('order_by')
    page = int(payload.get('page', 1))
    page_size = int(payload.get('page_size', 30))
    
    try:
        results = db.query_items(table_name='lots', filters=filters, order_by=order_by, limit=page_size, offset=page*page_size)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500