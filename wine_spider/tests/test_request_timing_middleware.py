from types import SimpleNamespace
from unittest.mock import Mock, patch

from scrapy import Request
from scrapy.http import Response

from wine_spider.middlewares.request_timing_middleware import RequestTimingMiddleware


def make_spider(custom_settings=None):
    return SimpleNamespace(
        custom_settings=custom_settings or {},
        logger=Mock(),
    )


def test_success_timing_can_be_disabled_by_spider_settings():
    middleware = RequestTimingMiddleware()
    request = Request("https://example.test/fast")
    request.meta["start_time"] = 100
    response = Response(request.url, status=200, request=request)
    spider = make_spider({"REQUEST_TIMING_SUCCESS_SAMPLE_RATE": 0})

    with patch("wine_spider.middlewares.request_timing_middleware.time.time", return_value=101):
        result = middleware.process_response(request, response, spider)

    assert result is response
    spider.logger.info.assert_not_called()


def test_slow_success_timing_is_logged_even_when_sampling_disabled():
    middleware = RequestTimingMiddleware()
    request = Request("https://example.test/slow")
    request.meta["start_time"] = 100
    response = Response(request.url, status=200, request=request)
    spider = make_spider({
        "REQUEST_TIMING_SUCCESS_SAMPLE_RATE": 0,
        "REQUEST_TIMING_SLOW_SECONDS": 30,
    })

    with patch("wine_spider.middlewares.request_timing_middleware.time.time", return_value=131):
        middleware.process_response(request, response, spider)

    spider.logger.info.assert_called_once()
    assert "slow" in spider.logger.info.call_args.args[0]


def test_exception_timing_is_always_logged():
    middleware = RequestTimingMiddleware()
    request = Request("https://example.test/error")
    request.meta["start_time"] = 100
    spider = make_spider({"REQUEST_TIMING_SUCCESS_SAMPLE_RATE": 0})

    with patch("wine_spider.middlewares.request_timing_middleware.time.time", return_value=102):
        result = middleware.process_exception(request, RuntimeError("boom"), spider)

    assert result is None
    spider.logger.warning.assert_called_once()
    assert "[EXCEPTION]" in spider.logger.warning.call_args.args[0]
