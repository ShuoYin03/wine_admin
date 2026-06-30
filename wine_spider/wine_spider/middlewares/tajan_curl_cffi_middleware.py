import logging

from curl_cffi import requests as cffi_requests
from scrapy.http import HtmlResponse
from twisted.internet.threads import deferToThread

from wine_spider.helpers.tajan.curl_cffi_profile import (
    DEFAULT_TAJAN_CURL_CFFI_IMPERSONATES,
    build_tajan_curl_cffi_headers,
    build_tajan_curl_cffi_profiles,
)


class TajanCurlCffiMiddleware:
    RETRY_STATUSES = {403, 408, 429, 500, 502, 503, 504, 522, 524}

    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.enabled = settings.getbool("TAJAN_CURL_CFFI_ENABLED", True)
        self.timeout = settings.getfloat("TAJAN_CURL_CFFI_TIMEOUT", 45.0)
        self.max_attempts = max(1, settings.getint("TAJAN_CURL_CFFI_MAX_ATTEMPTS", 3))
        self.accept_language = settings.get(
            "TAJAN_ACCEPT_LANGUAGE",
            None,
        )
        self.request_func = cffi_requests.request
        impersonates = settings.getlist("TAJAN_CURL_CFFI_IMPERSONATES")
        self.profiles = build_tajan_curl_cffi_profiles(
            raw_proxies=settings.get("TAJAN_CURL_CFFI_PROXIES"),
            impersonates=tuple(impersonates or DEFAULT_TAJAN_CURL_CFFI_IMPERSONATES),
        )
        self.profile_index = 0

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.settings)
        middleware.crawler = crawler
        return middleware

    def process_request(self, request, spider):
        if not self.enabled or not request.meta.get("curl_cffi"):
            return None
        return deferToThread(self._download, request)

    def _download(self, request):
        last_response = None
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            profile = self.next_profile()
            try:
                response = self._request_once(request, profile)
            except Exception as exc:
                last_error = exc
                self._inc_stat("tajan_curl_cffi/transport_error")
                if attempt < self.max_attempts:
                    self._inc_stat("tajan_curl_cffi/retry")
                    self.logger.info(
                        "Tajan curl_cffi retry after transport error: attempt=%s/%s url=%s error=%s",
                        attempt,
                        self.max_attempts,
                        request.url,
                        exc,
                    )
                    continue
                raise

            last_response = response
            self._inc_stat("tajan_curl_cffi/request")
            self._inc_stat(f"tajan_curl_cffi/status/{response.status_code}")
            self._inc_stat(f"tajan_curl_cffi/impersonate/{profile.impersonate}")

            if response.status_code not in self.RETRY_STATUSES:
                return self._to_scrapy_response(request, response)

            if attempt < self.max_attempts:
                self._inc_stat("tajan_curl_cffi/retry")
                self.logger.info(
                    "Tajan curl_cffi retry: status=%s attempt=%s/%s url=%s",
                    response.status_code,
                    attempt,
                    self.max_attempts,
                    request.url,
                )

        if last_response is None and last_error is not None:
            raise last_error
        return self._to_scrapy_response(request, last_response)

    def _request_once(self, request, profile):
        referer = request.meta.get("curl_cffi_referer") or self._header_value(request, "Referer")
        headers = build_tajan_curl_cffi_headers(
            profile.impersonate,
            referer=referer,
            accept_language=self.accept_language,
        )
        headers.update(request.meta.get("curl_cffi_headers") or {})
        return self.request_func(
            request.method,
            request.url,
            headers=headers,
            impersonate=profile.impersonate,
            proxies=profile.proxies,
            timeout=request.meta.get("curl_cffi_timeout", self.timeout),
            allow_redirects=True,
        )

    def _to_scrapy_response(self, request, response):
        return HtmlResponse(
            url=str(response.url),
            status=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            request=request,
            encoding=response.encoding or "utf-8",
        )

    def next_profile(self):
        profile = self.profiles[self.profile_index % len(self.profiles)]
        self.profile_index += 1
        return profile

    def _header_value(self, request, name):
        values = request.headers.getlist(name)
        if not values:
            return None
        return values[0].decode("utf-8", errors="ignore")

    def _inc_stat(self, key: str, count: int = 1) -> None:
        stats = getattr(getattr(self, "crawler", None), "stats", None)
        if stats is not None:
            stats.inc_value(key, count=count)
