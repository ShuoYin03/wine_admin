from __future__ import annotations

import requests
from scrapy.http import HtmlResponse, Request, TextResponse


def live_html(url: str, session: requests.Session | None = None, **kwargs) -> HtmlResponse:
    """Make a real GET request and wrap the response as a Scrapy HtmlResponse."""
    client = session or requests
    r = client.get(url, **kwargs)
    r.raise_for_status()
    return HtmlResponse(url=url, body=r.content)


def live_json(url: str, method: str = "get", session: requests.Session | None = None, **kwargs) -> TextResponse:
    """Make a real HTTP request and wrap the response as a Scrapy TextResponse."""
    client = session or requests
    r = getattr(client, method)(url, **kwargs)
    r.raise_for_status()
    return TextResponse(url=url, body=r.content, encoding="utf-8")


def make_json_response(url: str, data: bytes, meta: dict | None = None) -> TextResponse:
    """Wrap raw JSON bytes as a Scrapy TextResponse, optionally with request meta."""
    request = Request(url=url, meta=meta or {})
    return TextResponse(url=url, body=data, encoding="utf-8", request=request)
