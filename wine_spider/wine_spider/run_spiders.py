from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from wine_spider.spiders.baghera import BagheraSpider
from wine_spider.spiders.bonhams import BonhamsSpider
from wine_spider.spiders.christies import ChristiesSpider
from wine_spider.spiders.sothebys import SothebysSpider
from wine_spider.spiders.steinfels import SteinfelsSpider
from wine_spider.spiders.sylvies import SylviesSpider
from wine_spider.spiders.zachys import ZachysSpider
from wine_spider.spiders.tajan import TajanSpider
from wine_spider.spiders.wineauctioneer import WineAuctioneerSpider

process = CrawlerProcess(get_project_settings())

process.crawl(BagheraSpider)
process.crawl(BonhamsSpider)
process.crawl(ChristiesSpider)
process.crawl(SothebysSpider)
process.crawl(SteinfelsSpider)
process.crawl(SylviesSpider)
process.crawl(ZachysSpider)
process.crawl(TajanSpider)
process.crawl(WineAuctioneerSpider)

process.start()

