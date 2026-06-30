import asyncio
import logging
from scrapy import signals
from scrapy_playwright.page import PageMethod

class AwsWafBypassMiddleware:
    """Detect AWS WAF challenge pages and back off instead of scraping bad data."""

    DEFAULT_CHALLENGE_MARKERS = (
        "challenge-container",
        "awswaf",
        "aws-waf-token",
        "awsWafCookieDomainList",
        "Request blocked",
    )
    
    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.retry_counts = {}
        self.max_retries = settings.getint('AWS_WAF_MAX_RETRIES', 5)
        self.min_delay = settings.getint('AWS_WAF_MIN_DELAY', 2000)
        self.max_delay = settings.getint('AWS_WAF_MAX_DELAY', 5000)
        self.retry_base_delay = settings.getfloat('AWS_WAF_RETRY_BASE_DELAY', 30.0)
        self.retry_max_delay = settings.getfloat('AWS_WAF_RETRY_MAX_DELAY', 300.0)
        self.close_spider_on_block = settings.getbool('AWS_WAF_CLOSE_SPIDER_ON_BLOCK', True)
        self.block_statuses = {
            int(status) for status in settings.getlist('AWS_WAF_BLOCK_STATUSES', [403, 429])
        }
        self.challenge_markers = tuple(
            settings.getlist('AWS_WAF_CHALLENGE_MARKERS', self.DEFAULT_CHALLENGE_MARKERS)
        )
        self.enabled_spiders = settings.get('AWS_WAF_ENABLED_SPIDERS', [])
        
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler.settings)
        middleware.crawler = crawler
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def spider_opened(self, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            self.logger.info(f"WAF Bypass Middleware not enabled for {spider.name}")
            return
        
        self.logger.info(f"AWS WAF monitor enabled for {spider.name}")
        
    def spider_closed(self, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return
            
        self.logger.info(f"AWS WAF monitor closed for {spider.name}")
    
    def process_request(self, request, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return None
        
        if not request.meta.get('playwright', False):
            return None

        if not request.meta.get("skip_waf_page_methods"):
            request.meta.setdefault("playwright_page_methods", []).extend(
                self._get_playwright_page_methods()
            )
            
        return None
    
    async def process_response(self, request, response, spider):
        if self.enabled_spiders and spider.name not in self.enabled_spiders:
            return response

        if not self._is_waf_challenge(response):
            return response

        self._inc_stat("aws_waf/challenge")
        retry_count = self.retry_counts.get(request.url, 0) + 1
        self.retry_counts[request.url] = retry_count

        if retry_count <= self.max_retries:
            retry_delay = min(
                self.retry_max_delay,
                self.retry_base_delay * (2 ** (retry_count - 1)),
            )
            self.logger.warning(
                "Detected AWS WAF block for %s with status %s; retry %s/%s after %.1fs",
                request.url,
                response.status,
                retry_count,
                self.max_retries,
                retry_delay,
            )
            self._inc_stat("aws_waf/retry")
            if retry_delay > 0:
                await asyncio.sleep(retry_delay)
            await self._close_playwright_page(response, request)
            return request.replace(dont_filter=True)

        self.logger.error(
            "AWS WAF block persisted for %s after %s retries; closing spider",
            request.url,
            self.max_retries,
        )
        self._inc_stat("aws_waf/max_retries")
        await self._close_playwright_page(response, request)
        if self.close_spider_on_block:
            self.crawler.engine.close_spider(spider, reason="aws_waf_blocked")
        return response

    def _get_playwright_page_methods(self) -> list[PageMethod]:
        wait_ms = max(0, min(self.min_delay, self.max_delay))
        return [PageMethod("wait_for_timeout", wait_ms)] if wait_ms else []

    def _is_waf_challenge(self, response) -> bool:
        if response.status in self.block_statuses:
            return True

        text = self._response_text(response)
        if response.status == 202 and text:
            return self._has_challenge_marker(text)

        return self._has_challenge_marker(text)

    def _has_challenge_marker(self, text: str) -> bool:
        lower_text = text.lower()
        return any(marker.lower() in lower_text for marker in self.challenge_markers)

    def _response_text(self, response) -> str:
        try:
            return response.text
        except AttributeError:
            body = getattr(response, "body", b"")
            if isinstance(body, bytes):
                return body[:4096].decode("utf-8", errors="ignore")
            return str(body)
        except Exception:
            return ""

    def _inc_stat(self, key: str, count: int = 1) -> None:
        stats = getattr(getattr(self, "crawler", None), "stats", None)
        if stats is not None:
            stats.inc_value(key, count=count)

    async def _close_playwright_page(self, response, request=None) -> None:
        try:
            meta = response.meta
        except AttributeError:
            meta = getattr(request, "meta", {}) or {}
            if not meta:
                response_request = getattr(response, "request", None)
                meta = getattr(response_request, "meta", {}) or {}

        page = meta.get("playwright_page")
        if page is not None:
            await page.close()
