import json
import logging
from functools import partial
from app.service import CsvExportService
from app.utils import serialize_for_json, parse_query_payload, json_response
from app.mappers.auction_mapper import map_auction
from flask import Blueprint, request, Response, current_app

logger = logging.getLogger(__name__)

fx_rates_query_blueprint = Blueprint('fx_rates_query', __name__)

@fx_rates_query_blueprint.route('/rates', methods=['GET'])
async def auction(auction_id: str) -> Response:
    try:
        params = request.args
        rates_from, rates_to = params.get('rates_from'), params.get('rates_to')
        data = current_app.fx_rates_client.query_fx_rates(rates_from, rates_to)