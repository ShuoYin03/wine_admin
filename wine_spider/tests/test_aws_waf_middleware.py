import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

from scrapy import Request
from scrapy.http import TextResponse
from scrapy.settings import Settings

from wine_spider.middlewares.aws_waf_bypass import AwsWafBypassMiddleware


class DummyPage:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


def make_spider(name="zachys_spider"):
    return SimpleNamespace(name=name)


def make_middleware(**overrides):
    values = {
        "AWS_WAF_ENABLED_SPIDERS": ["zachys_spider"],
        "AWS_WAF_MAX_RETRIES": 1,
        "AWS_WAF_MIN_DELAY": 1,
        "AWS_WAF_MAX_DELAY": 1,
        "AWS_WAF_RETRY_BASE_DELAY": 0,
        "AWS_WAF_RETRY_MAX_DELAY": 0,
        "AWS_WAF_CLOSE_SPIDER_ON_BLOCK": True,
    }
    values.update(overrides)
    middleware = AwsWafBypassMiddleware(Settings(values))
    middleware.crawler = SimpleNamespace(stats=Mock(), engine=Mock())
    return middleware


def make_response(status=202, body="awsWafCookieDomainList", page=None):
    request = Request(
        "https://bid.zachys.com/auctions?page=1&status=5",
        meta={"playwright_page": page} if page is not None else {},
    )
    return TextResponse(
        request.url,
        status=status,
        body=body.encode("utf-8"),
        encoding="utf-8",
        request=request,
    )


def make_detached_response(url, status=403, body="Forbidden"):
    return TextResponse(
        url,
        status=status,
        body=body.encode("utf-8"),
        encoding="utf-8",
    )


def test_process_request_uses_current_scrapy_playwright_meta_key():
    middleware = make_middleware()
    spider = make_spider()
    request = Request(
        "https://bid.zachys.com/auctions?page=1&status=5",
        meta={"playwright": True},
    )

    result = middleware.process_request(request, spider)

    assert result is None
    assert "playwright_page_methods" in request.meta
    assert "playwright_page_coroutines" not in request.meta


def test_process_request_ignores_spiders_not_enabled():
    middleware = make_middleware()
    spider = make_spider("other_spider")
    request = Request(
        "https://bid.zachys.com/auctions?page=1&status=5",
        meta={"playwright": True},
    )

    middleware.process_request(request, spider)

    assert "playwright_page_methods" not in request.meta


def test_waf_challenge_is_retried_and_original_page_is_closed():
    middleware = make_middleware(AWS_WAF_MAX_RETRIES=1)
    spider = make_spider()
    page = DummyPage()
    response = make_response(page=page)
    request = response.request

    result = asyncio.run(middleware.process_response(request, response, spider))

    assert isinstance(result, Request)
    assert result.dont_filter is True
    assert page.closed is True
    middleware.crawler.engine.close_spider.assert_not_called()
    middleware.crawler.stats.inc_value.assert_any_call("aws_waf/challenge", count=1)
    middleware.crawler.stats.inc_value.assert_any_call("aws_waf/retry", count=1)


def test_waf_challenge_with_detached_response_closes_request_page():
    middleware = make_middleware(AWS_WAF_MAX_RETRIES=1)
    spider = make_spider()
    page = DummyPage()
    request = Request(
        "https://bid.zachys.com/auctions?page=1&status=5",
        meta={"playwright_page": page},
    )
    response = make_detached_response(request.url)

    result = asyncio.run(middleware.process_response(request, response, spider))

    assert isinstance(result, Request)
    assert result.dont_filter is True
    assert page.closed is True


def test_configured_202_status_is_retried_even_without_marker():
    middleware = make_middleware(
        AWS_WAF_MAX_RETRIES=1,
        AWS_WAF_BLOCK_STATUSES=[202, 403, 429],
    )
    spider = make_spider()
    page = DummyPage()
    response = make_response(status=202, body="", page=page)
    request = response.request

    result = asyncio.run(middleware.process_response(request, response, spider))

    assert isinstance(result, Request)
    assert result.dont_filter is True
    assert page.closed is True


def test_waf_challenge_closes_spider_after_retry_budget():
    middleware = make_middleware(AWS_WAF_MAX_RETRIES=0)
    spider = make_spider()
    page = DummyPage()
    response = make_response(status=403, body="Forbidden", page=page)
    request = response.request

    result = asyncio.run(middleware.process_response(request, response, spider))

    assert result is response
    assert page.closed is True
    middleware.crawler.engine.close_spider.assert_called_once_with(
        spider,
        reason="aws_waf_blocked",
    )
    middleware.crawler.stats.inc_value.assert_any_call("aws_waf/max_retries", count=1)
