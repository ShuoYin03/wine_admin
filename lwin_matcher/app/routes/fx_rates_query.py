from __future__ import annotations
import datetime
import json
import logging
from app.utils import parse_query_payload, json_response
from app.service.fx_rates_service import FxRatesService
from flask import Blueprint, Response, request

logger = logging.getLogger(__name__)

fx_rates_query_blueprint = Blueprint('fx_rates_query', __name__)


@fx_rates_query_blueprint.route('/rate', methods=['GET'])
async def get_rate() -> Response:
    try:
        rates_from = request.args.get('rates_from')
        rates_to = request.args.get('rates_to')
        date_str = request.args.get('date')

        if not rates_from or not rates_to or not date_str:
            return Response(
                json.dumps({"error": "rates_from, rates_to, and date are required"}),
                mimetype='application/json',
                status=400,
            )

        try:
            query_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response(
                json.dumps({"error": "Invalid date format, expected YYYY-MM-DD"}),
                mimetype='application/json',
                status=400,
            )

        service = FxRatesService()
        result = service.get_rate(
            rates_from=rates_from,
            rates_to=rates_to,
            date=query_date,
        )

        if result is None:
            return Response(json.dumps({"error": "Rate not found"}), mimetype='application/json', status=404)

        return json_response(result.model_dump(mode='json'))

    except Exception as e:
        logger.exception(f"[/rate] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)

        
@fx_rates_query_blueprint.route('/rates', methods=['POST'])
async def rates() -> Response:
    try:
        q = parse_query_payload()
        service = FxRatesService()
        data, count = service.get_rates(
            filters=q.filters,
            order_by=q.order_by,
            limit=q.page_size,
            offset=q.offset,
            return_count=True,
        )
        return json_response([r.model_dump(mode='json') for r in data], count=count)
    except Exception as e:
        logger.exception(f"[/rates] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)
