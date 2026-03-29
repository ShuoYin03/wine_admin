from __future__ import annotations
import json
from flask import Response


def json_response(data: object, count: int | None = None, status: int = 200) -> Response:
    body = {"meta": {"count": count}, "data": data}
    return Response(json.dumps(body), mimetype='application/json', status=status)
