import scrapy
import dotenv
from datetime import datetime
from shared.currency.currency_service import CurrencyService
from shared.currency.models import CurrencyCode
from wine_spider.items import FxRateItemList
from wine_spider.spiders.logging_utils import build_spider_log_file

dotenv.load_dotenv()

class FxRatesSpider(scrapy.Spider):
    name = "fx_rates_spider"
    allowed_domains = [
        "api.ofx.com",
    ]

    custom_settings = {
        "LOG_FILE": build_spider_log_file("fx_rates.log"),
    }
    
    def __init__(self, *args, **kwargs):
        super(FxRatesSpider, self).__init__(*args, **kwargs)
        self.rates_list = [
            CurrencyCode.CHF, CurrencyCode.CNY, 
            CurrencyCode.EUR, CurrencyCode.GBP, 
            CurrencyCode.HKD, CurrencyCode.SGD, 
            CurrencyCode.ZAR
        ]
        self.currency_api = CurrencyService()
        self.base_currency = CurrencyCode.USD
        self.start_date = datetime(2017, 1, 1)

    def start_requests(self):
        for rate in self.rates_list:
            end_date = datetime.now()

            try:
                exchange_rates = self.currency_api.get_exchange_rates(
                    from_currency=rate,
                    to_currency=self.base_currency,
                    start_date=self.start_date,
                    end_date=end_date,
                )
            except ValueError as exc:
                self.logger.error(f"Failed to fetch {rate.value}->{self.base_currency.value}: {exc}")
                continue

            rows = []
            for date_string, rate_value in exchange_rates.items():
                rate_date = datetime.strptime(date_string, "%Y-%m-%d").date()
                rows.append(
                    {
                        "rates_from": rate.value,
                        "rates_to": self.base_currency.value,
                        "date": rate_date,
                        "rates": float(rate_value),
                    }
                )

            fx_rate_item = FxRateItemList()
            fx_rate_item["rows"] = rows
            yield fx_rate_item

            self.logger.info(
                f"Produced {len(rows)} FX rows for {rate.value}->{self.base_currency.value}"
            )
