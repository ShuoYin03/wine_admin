# import sys
# import json
# sys.path.append('../..')
# from flask import Blueprint, request, Response
# from database.base_database_client import DatabaseClient
# from lwin_matcher.app.service.fx_rates_service import FxRatesService

# fx_rates_blueprint = Blueprint('fx_rates', __name__)
# fx_rates_service = FxRatesService()
# db = DatabaseClient()

# @fx_rates_blueprint.route('/rates', methods=['GET'])
# async def rates():
#     rates_from = request.args.get('rates_from')
#     rates_to = request.args.get('rates_to')
    
#     try:
#         results = fx_rates_service.get_rates(rates_from, rates_to)
#         return Response(results, status=200)
#     except Exception as e:
#         try:
#             result = db.query_items(
#                 table_name='fx_rates_cache',
#                 filters={
#                     'rates_from': rates_from, 
#                     'rates_to': rates_to
#                 }
#             )

#             result = str(result[0]['rates'])
#             return Response(result, status=200)
#         except Exception as e:
#             return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
        
# @fx_rates_blueprint.route('/rates_query', methods=['GET'])
# async def rates_query():
#     try:
#         results = db.query_items(table_name='fx_rates_cache')
#         return Response(json.dumps({"data": results}), status=200)
#     except Exception as e:
#         return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)