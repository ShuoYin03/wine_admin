from scrapy import Request
from scrapy.settings import Settings

from wine_spider.helpers.tajan.curl_cffi_profile import (
    build_tajan_curl_cffi_headers,
    build_tajan_curl_cffi_profiles,
    build_tajan_proxy_urls,
)
from wine_spider.middlewares.tajan_curl_cffi_middleware import (
    TajanCurlCffiMiddleware,
)


class FakeCurlResponse:
    def __init__(self, status_code=200, body=b"", url="https://www.tajan.com/detail"):
        self.status_code = status_code
        self.content = body
        self.url = url
        self.headers = {"content-type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"


def test_tajan_proxy_urls_support_authenticated_host_port_entries():
    proxies = build_tajan_proxy_urls("31.59.20.176:6754:user:pass")

    assert proxies == ["http://user:pass@31.59.20.176:6754"]


def test_tajan_curl_cffi_headers_match_impersonated_chrome_profile():
    headers = build_tajan_curl_cffi_headers(
        "chrome142",
        referer="https://www.tajan.com/v1/auction-catalog/wines?pageNum=1",
    )

    assert "Chrome/142.0.0.0" in headers["user-agent"]
    assert '"Google Chrome";v="142"' in headers["sec-ch-ua"]
    assert headers["accept"].startswith("text/html")
    assert headers["accept-language"]
    assert headers["referer"] == "https://www.tajan.com/v1/auction-catalog/wines?pageNum=1"
    assert headers["sec-fetch-dest"] == "document"
    assert headers["sec-fetch-mode"] == "navigate"
    assert headers["sec-fetch-site"] == "same-origin"
    assert headers["upgrade-insecure-requests"] == "1"


def test_tajan_curl_cffi_profiles_rotate_fingerprint_and_proxy():
    profiles = build_tajan_curl_cffi_profiles(
        raw_proxies="\n".join(
            [
                "31.59.20.176:6754:user:pass",
                "31.56.127.193:7684:user:pass",
            ]
        ),
        impersonates=("chrome142", "chrome136"),
    )

    assert [profile.impersonate for profile in profiles[:4]] == [
        "chrome142",
        "chrome136",
        "chrome136",
        "chrome142",
    ]
    assert profiles[0].proxies == {
        "http": "http://user:pass@31.59.20.176:6754",
        "https": "http://user:pass@31.59.20.176:6754",
    }
    assert profiles[1].proxies == {
        "http": "http://user:pass@31.56.127.193:7684",
        "https": "http://user:pass@31.56.127.193:7684",
    }


def test_tajan_curl_cffi_middleware_retries_429_with_next_profile():
    settings = Settings(
        {
            "TAJAN_CURL_CFFI_PROXIES": "\n".join(
                [
                    "31.59.20.176:6754:user:pass",
                    "31.56.127.193:7684:user:pass",
                ]
            ),
            "TAJAN_CURL_CFFI_IMPERSONATES": ["chrome142", "chrome136"],
            "TAJAN_CURL_CFFI_MAX_ATTEMPTS": 2,
        }
    )
    middleware = TajanCurlCffiMiddleware(settings)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return FakeCurlResponse(status_code=429, body=b"blocked", url=url)
        return FakeCurlResponse(
            status_code=200,
            body=b"<div class='lot-info border-bottom'>6 bouteilles PETRUS 2007</div>",
            url=url,
        )

    middleware.request_func = fake_request
    request = Request(
        url="https://www.tajan.com/en/auction-lot/6-bouteilles-petrus",
        meta={
            "curl_cffi": True,
            "curl_cffi_referer": "https://www.tajan.com/v1/auction-catalog/wines",
        },
    )

    response = middleware._download(request)

    assert response.status == 200
    assert b"PETRUS" in response.body
    assert len(calls) == 2
    assert calls[0]["impersonate"] == "chrome142"
    assert calls[1]["impersonate"] == "chrome136"
    assert calls[0]["proxies"] != calls[1]["proxies"]
    assert calls[0]["headers"]["referer"] == "https://www.tajan.com/v1/auction-catalog/wines"


def test_tajan_curl_cffi_middleware_retries_transport_error_with_next_profile():
    settings = Settings(
        {
            "TAJAN_CURL_CFFI_PROXIES": "\n".join(
                [
                    "31.59.20.176:6754:user:pass",
                    "31.56.127.193:7684:user:pass",
                ]
            ),
            "TAJAN_CURL_CFFI_IMPERSONATES": ["chrome142", "chrome136"],
            "TAJAN_CURL_CFFI_MAX_ATTEMPTS": 2,
        }
    )
    middleware = TajanCurlCffiMiddleware(settings)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise TimeoutError("proxy timed out")
        return FakeCurlResponse(status_code=200, body=b"ok", url=url)

    middleware.request_func = fake_request
    request = Request(
        url="https://www.tajan.com/en/auction-lot/6-bouteilles-petrus",
        meta={"curl_cffi": True},
    )

    response = middleware._download(request)

    assert response.status == 200
    assert len(calls) == 2
    assert calls[0]["impersonate"] == "chrome142"
    assert calls[1]["impersonate"] == "chrome136"
    assert calls[0]["proxies"] != calls[1]["proxies"]
