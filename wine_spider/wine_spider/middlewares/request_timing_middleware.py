import time
import zlib
from scrapy import signals

class RequestTimingMiddleware:
    def process_request(self, request, spider):
        request.meta['start_time'] = time.time()
        return None

    def process_response(self, request, response, spider):
        start_time = request.meta.get('start_time')
        if start_time:
            duration = time.time() - start_time
            if self.should_log_success(request, duration, spider):
                spider.logger.info(f"[{response.status}] {request.url} took {duration:.3f} seconds")
        return response

    def process_exception(self, request, exception, spider):
        start_time = request.meta.get('start_time')
        if start_time:
            duration = time.time() - start_time
            spider.logger.warning(f"[EXCEPTION] {request.url} failed after {duration:.3f} seconds: {exception}")
        return None

    def should_log_success(self, request, duration, spider):
        slow_seconds = self.get_float_setting(spider, "REQUEST_TIMING_SLOW_SECONDS", None)
        if slow_seconds is not None and duration >= slow_seconds:
            return True

        sample_rate = self.get_int_setting(spider, "REQUEST_TIMING_SUCCESS_SAMPLE_RATE", 1)
        if sample_rate <= 0:
            return False
        if sample_rate == 1:
            return True

        return zlib.crc32(request.url.encode("utf-8")) % sample_rate == 0

    def get_int_setting(self, spider, name, default):
        value = self.get_setting(spider, name, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_float_setting(self, spider, name, default):
        value = self.get_setting(spider, name, default)
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def get_setting(self, spider, name, default):
        custom_settings = getattr(spider, "custom_settings", None) or {}
        if name in custom_settings:
            return custom_settings[name]

        crawler = getattr(spider, "crawler", None)
        settings = getattr(crawler, "settings", None)
        if settings is not None:
            return settings.get(name, default)

        return default
