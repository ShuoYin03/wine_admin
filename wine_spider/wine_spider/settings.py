TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

BOT_NAME = "wine_spider"

SPIDER_MODULES = ["wine_spider.spiders"]
NEWSPIDER_MODULE = "wine_spider.spiders"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"

ROBOTSTXT_OBEY = True

# SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
# SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

CONCURRENT_REQUESTS = 16

FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "DEBUG"

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0   # Initial download delay
AUTOTHROTTLE_MAX_DELAY = 5.0    # Maximum download delay in high latencies
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# JOBDIR = 'wine_spider/crawl_state/sothebys'

DOWNLOADER_MIDDLEWARES = {
   'wine_spider.middlewares.SothebysLoginMiddleware': 100,
   'wine_spider.middlewares.PlaywrightResourceBlockerMiddleware': 200,
}

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_LAUNCH_OPTIONS = { 
   "headless": True 
}

ITEM_PIPELINES = {
   "wine_spider.pipelines.AuctionStoragePipeline": 100,
   "wine_spider.pipelines.LotStoragePipeline": 200,
   "wine_spider.pipelines.LotDetailStoragePipeline": 300,
   "wine_spider.pipelines.LwinMatchingPipeline": 400,
   "wine_spider.pipelines.AuctionSalesPipeline": 500,
   # "wine_spider.pipelines.FxRatesStoragePipeline": 500,
}

SOTHEBYS_STATE_PATH         = "wine_spider/login_state/sothebys_cookies.json"
SOTHEBYS_STATE_EXPIRE_DAYS  = 10
SOTHEBYS_LOGIN_SCRIPT       = "wine_spider/helpers/sothebys/login.py"

PLAYWRIGHT_CONTEXTS = {
    "sothebys": {
        "storage_state": "wine_spider/login_state/sothebys_cookies.json",
    },
}
PLAYWRIGHT_PROCESS_RESPONSE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'scrapy-playwright': {
            'level': 'WARNING',
        }
    },
}

import logging
logging.getLogger('scrapy-playwright').setLevel(logging.WARNING)

# PLAYWRIGHT_BROWSER_TYPE = "chromium"

# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"