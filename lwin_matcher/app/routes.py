from database import DatabaseClient
from app.model import LwinMatchingParams
from .service import LwinMatchingService
from flask import Blueprint, jsonify, request

main = Blueprint('main', __name__)
lwin_matching_service = LwinMatchingService()

@main.route('/')
def index():
    return "Hello, World!"

@main.route('/match', methods=['GET'])
def match():
    wine_name = request.args.get('wine_name', '')
    lot_producer = request.args.get('lot_producer', '')
    vintage = request.args.get('vintage', '')
    region = request.args.get('region', '')
    sub_region = request.args.get('sub_region', '')
    country = request.args.get('country', '')
    colour = request.args.get('colour', '')

    lwin_matching_params = LwinMatchingParams(
        wine_name=wine_name,
        lot_producer=lot_producer,
        vintage=vintage,
        region=region,
        sub_region=sub_region,
        country=country,
        colour=colour
    )

    try:
        matched, lwin_code = lwin_matching_service.lwin_matching(lwin_matching_params)
        result = {
            "matched": matched.value,
            "lwin_code": lwin_code
        }
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@main.route('/one', methods=['GET'])
def one():
    database_client = DatabaseClient()
    table_names = database_client.get_one_records('lots')
    return table_names