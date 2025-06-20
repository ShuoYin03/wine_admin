import os
import scrapy
import dotenv
from wine_spider.services import fx_rates_client
from wine_spider.items import FxRateItem

dotenv.load_dotenv()

class FxRatesSpider(scrapy.Spider):
    name = "fx_rates_spider"
    allowed_domains = [
        os.getenv('BASE_URL')
    ]
    
    def __init__(self, *args, **kwargs):
        super(FxRatesSpider, self).__init__(*args, **kwargs)
        self.db = fx_rates_client
        self.rates_list = set(i for i in self.db.query_items(table_name="lots", distinct_fields="original_currency") if i != 'USD')
        self.base_url = f"{os.getenv('BASE_URL')}/rates"

    def start_requests(self):
        for rate in self.rates_list:
            params = f"rates_from={rate}&rates_to=USD"
            yield scrapy.Request(
                url=f"{self.base_url}?{params}", 
                callback=self.parse,
                meta={
                    'rates_from': rate,
                    'rates_to': 'USD'
                },
                dont_filter=True
            )

    def parse(self, response):
        rates_from = response.meta['rates_from']
        rates_to = response.meta['rates_to']

        exist_rate = self.db.query_items(
            table_name="fx_rates_cache",
            filters=[
                ["rates_from", "eq", rates_from],
                ["rates_to", "eq", rates_to]
            ]
        )
        
        if exist_rate:
            self.db.delete_item(
                table_name="fx_rates_cache",
                item_id=exist_rate[0]['id']
            )

        rates = float(response.text)

        fx_rate_item = FxRateItem()
        fx_rate_item['rates_from'] = rates_from
        fx_rate_item['rates_to'] = rates_to
        fx_rate_item['rates'] = rates

        yield fx_rate_item