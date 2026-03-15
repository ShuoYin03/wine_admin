import json
import logging
from functools import partial
from typing import Any
from app.service import CsvExportService
from app.utils import justify_ops, serialize_for_json
from app.mappers.auction_mapper import map_auction
from flask import Blueprint, request, Response, current_app

logger = logging.getLogger(__name__)

auction_query_blueprint = Blueprint('auction_query', __name__)

@auction_query_blueprint.route('/auction/<auction_id>', methods=['GET'])
async def auction(auction_id: str) -> Response:
    try:
        include_lots = request.headers.get('X-Include-Lots', 'false').lower() == 'true'

        mapper = partial(map_auction, include_lots=include_lots)
        data = current_app.auctions_client.query_single_auction(auction_id, mapper=mapper)
        if data is None:
            return Response(json.dumps({"error": "Not found"}), mimetype='application/json', status=404)
        return Response(
            json.dumps({"auction": data.model_dump(mode='json')}),
            mimetype='application/json'
        )

    except Exception as e:
        logger.exception(f"[/auction/{auction_id}] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


@auction_query_blueprint.route('/auctions', methods=['GET', 'POST'])
async def auctions() -> Response:
    try:
        include_lots = request.headers.get('X-Include-Lots', 'false').lower() == 'true'
        mapper = partial(map_auction, include_lots=include_lots)

        if request.method == 'GET':
            data, count = current_app.auctions_client.query_auctions_with_sales(mapper=mapper)
            logger.info(f"[GET /auctions] returned {len(data)} records")
            return Response(
                json.dumps({
                    "auctions": [a.model_dump(mode='json') for a in data], 
                    "count": count
                }), 
                mimetype='application/json'
            )

        payload: dict[str, Any] = request.get_json() or {}
        filters = justify_ops(payload.get('filters', []))
        order_by: str | None = payload.get('order_by')
        page: int = int(payload.get('page', 1))
        page_size: int = int(payload.get('page_size', 30))
        return_count: bool = payload.get('return_count', False)
        offset: int = (page - 1) * page_size

        data, count = current_app.auctions_client.query_auctions_with_sales(
            mapper=mapper,
            filters=filters,
            order_by=order_by,
            limit=page_size,
            offset=offset,
            return_count=True,
        )

        auctions = [a.model_dump(mode='json') for a in data]

        if return_count:
            return Response(json.dumps({"auctions": auctions, "count": count}), mimetype='application/json')

        return Response(json.dumps({"auctions": auctions}), mimetype='application/json')

    except Exception as e:
        logger.exception(f"[/auctions] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


@auction_query_blueprint.route('/auctions/export', methods=['POST'])
async def auctions_export() -> Response:
    """Export filtered auctions to CSV. Accepts same POST body as /auctions."""
    try:
        payload: dict[str, Any] = request.get_json() or {}
        filters = justify_ops(payload.get('filters', []))
        order_by: str | None = payload.get('order_by')

        mapper = partial(map_auction, include_lots=False)
        data, _ = current_app.auctions_client.query_auctions_with_sales(
            mapper=mapper,
            filters=filters,
            order_by=order_by,
        )
        rows = [a.model_dump(mode='json') for a in data]
        return CsvExportService.to_response(rows, filename="auctions.csv")

    except Exception as e:
        logger.exception(f"[/auctions/export] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


@auction_query_blueprint.route('/auction/<auction_id>/lots/export', methods=['GET'])
async def auction_lots_export(auction_id: str) -> Response:
    """Export all lots of a single auction to CSV."""
    try:
        results = current_app.lots_client.query_lots_with_items_and_auction(
            filters=[["auction_id", "eq", auction_id]]
        )
        return CsvExportService.to_response(
            serialize_for_json(results),
            filename=f"auction_{auction_id}_lots.csv",
        )

    except Exception as e:
        logger.exception(f"[/auction/{auction_id}/lots/export] error: {e}")
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)