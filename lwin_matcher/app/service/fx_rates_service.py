import sys
import requests
sys.path.append('../..')
from datetime import datetime, timedelta
from lwin_matcher.app.exception.rates_not_found_exception import RatesNotFoundException

class FxRatesService:
    def __init__(self):
        pass

    def url_construct(self, rates_from: str, rates_to: str) -> str:
        current_date = datetime.now().strftime('%Y-%m-%d')
        previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return f"https://fxds-hcc.oanda.com/api/data/update/?&source=OANDA&adjustment=0&base_currency={rates_to}&start_date={previous_date}&end_date={current_date}&period=daily&price=bid&view=graph&quote_currency_0={rates_from}"

    def get_rates(self, rates_from: str, rates_to: str) -> float:
        url = self.url_construct(rates_from, rates_to)
        response = requests.get(url)

        if response.status_code != 200:
            raise RatesNotFoundException(rates_from, rates_to)
        
        rates = response.json()['widget'][0]['data'][0][1]
        return rates