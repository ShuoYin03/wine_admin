import sys
import json
sys.path.append('../..')
from flask import Blueprint, request, Response
from database.database_client import DatabaseClient
from lwin_matcher.app.service.fx_rates_service import FxRatesService

fx_rates_blueprint = Blueprint('fx_rates', __name__)
fx_rates_service = FxRatesService()
db = DatabaseClient()

@fx_rates_blueprint.route('/rates', methods=['GET'])
async def lwin_query_all():
    rates_from = request.args.get('rates_from')
    rates_to = request.args.get('rates_to')
    
    try:
        results = fx_rates_service.get_rates(rates_from, rates_to)
        return Response(results, status=200)
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)