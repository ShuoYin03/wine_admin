from curl_cffi import requests
from datetime import datetime, timedelta
from shared.currency.models import CurrencyCode
from shared.utils.time_helper import timestamp_to_datetime
from shared.database.fx_rates_client import FxRatesClient

class CurrencyService:
    API_BASE_URL = "https://api.ofx.com/PublicSite.ApiService/SpotRateHistory/"

    def __init__(self, fx_rates_client=None):
        self._fx_rates_client = fx_rates_client

    @property
    def fx_rates_client(self):
        if self._fx_rates_client is None:
            self._fx_rates_client = FxRatesClient()
        return self._fx_rates_client

    def get_api_headers(self):
        return {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7",
            "origin": "https://www.ofx.com",
            "priority": "u=1, i",
            "referer": "https://www.ofx.com/",
            "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        }
    
    def get_request_details(
        self, 
        from_currency: CurrencyCode, 
        to_currency: CurrencyCode,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple[str, dict]:
        normalized_start = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
        normalized_end = datetime( end_date.year, end_date.month, end_date.day, 8, 34, 0)

        if normalized_end <= normalized_start:
            raise ValueError("end_date must be after start_date")

        params = {
            "DecimalPlaces": 6,
            "ReportingInterval": "daily",
            "format": "json"
        }

        url = f"{self.API_BASE_URL}{from_currency.value}/{to_currency.value}/{int(normalized_start.timestamp() * 1000)}/{int(normalized_end.timestamp() * 1000)}"
        
        return url, params
    
    def get_single_exchange_rate(
        self,
        from_currency: CurrencyCode, 
        to_currency: CurrencyCode,
        date: datetime
    ) -> float:
        try:
            fx_rate = self.fx_rates_client.get_by_date_and_currencies(from_currency.value, to_currency.value, date)
            if fx_rate:
                return fx_rate.rates
        except Exception:
            pass

        exchange_rates = self.get_exchange_rates(
            from_currency=from_currency,
            to_currency=to_currency,
            start_date=date,
            end_date=date + timedelta(days=1)
        )
        rate = exchange_rates.get(date.strftime("%Y-%m-%d"))

        if rate is None:
            raise ValueError(f"No exchange rate found for {from_currency.value}->{to_currency.value} on {date.strftime('%Y-%m-%d')}")
        
        return rate
    
    def get_exchange_rates(
        self,
        from_currency: CurrencyCode, 
        to_currency: CurrencyCode,
        start_date: datetime,
        end_date: datetime
    ) -> dict[str, float]:
        exchange_rates = {}
        headers = self.get_api_headers()
            
        url, params = self.get_request_details(from_currency, to_currency, start_date, end_date)

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("HistoricalPoints", []):
                exchange_rates[timestamp_to_datetime(item["PointInTime"], "milliseconds", "%Y-%m-%d")] = item["InterbankRate"]
        except requests.exceptions.RequestException as exc:
            raise ValueError(f"Failed to fetch exchange rates from OFX API: {exc}") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Unexpected API response structure: {exc}") from exc
        
        return exchange_rates

if __name__ == "__main__":
    service = CurrencyService()
    exchange_rate = service.get_single_exchange_rate(CurrencyCode.EUR, CurrencyCode.USD, datetime(2026, 1, 1))
    print(exchange_rate)
