from scrapy_playwright.page import PageMethod


def should_abort_request(request):
    return request.resource_type in ["image", "stylesheet", "font", "media"]
    
class PlaywrightResourceBlockerMiddleware:
    def process_request(self, request, spider):
        if request.meta.get("playwright"):
            request.meta.setdefault("playwright_page_methods", []).append(
                PageMethod("route", "**/*", self._abort_resources)
            )

    async def _abort_resources(self, route, request):
        if should_abort_request(request):
            await route.abort()
        else:
            await route.continue_()
