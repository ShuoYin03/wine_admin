import time
from scrapy import signals

class RequestTimingMiddleware:
    def process_request(self, request, spider):
        request.meta['start_time'] = time.time()
        return None

    def process_response(self, request, response, spider):
        start_time = request.meta.get('start_time')
        if start_time:
            duration = time.time() - start_time
            spider.logger.info(f"[{response.status}] {request.url} took {duration:.3f} seconds")
        return response

    def process_exception(self, request, exception, spider):
        start_time = request.meta.get('start_time')
        if start_time:
            duration = time.time() - start_time
            spider.logger.warning(f"[EXCEPTION] {request.url} failed after {duration:.3f} seconds: {exception}")
        return None