"""Tests for FxRatesService — all HTTP calls are mocked."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from app.service.fx_rates_service import FxRatesService
from app.exception.rates_not_found_exception import RatesNotFoundException


class TestFxRatesServiceUrlConstruct:
    def setup_method(self):
        self.service = FxRatesService()

    def test_url_contains_currencies(self):
        url = self.service.url_construct("USD", "EUR")
        assert "USD" in url
        assert "EUR" in url

    def test_base_currency_is_rates_to(self):
        url = self.service.url_construct("USD", "EUR")
        assert "base_currency=EUR" in url

    def test_quote_currency_is_rates_from(self):
        url = self.service.url_construct("USD", "EUR")
        assert "quote_currency_0=USD" in url

    def test_url_contains_oanda_domain(self):
        url = self.service.url_construct("GBP", "HKD")
        assert "oanda.com" in url

    def test_url_has_daily_period(self):
        url = self.service.url_construct("USD", "EUR")
        assert "period=daily" in url


class TestFxRatesServiceGetRates:
    def setup_method(self):
        self.service = FxRatesService()

    def test_successful_response_returns_rate(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "widget": [{"data": [[None, 1.085]]}]
        }
        with patch("app.service.fx_rates_service.requests.get", return_value=mock_response):
            rate = self.service.get_rates("USD", "EUR")
        assert rate == 1.085

    def test_non_200_raises_rates_not_found(self):
        mock_response = MagicMock()
        mock_response.status_code = 503
        with patch("app.service.fx_rates_service.requests.get", return_value=mock_response):
            with pytest.raises(RatesNotFoundException):
                self.service.get_rates("USD", "EUR")

    def test_404_raises_rates_not_found(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        with patch("app.service.fx_rates_service.requests.get", return_value=mock_response):
            with pytest.raises(RatesNotFoundException):
                self.service.get_rates("ABC", "XYZ")

    def test_get_called_with_correct_url(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"widget": [{"data": [[None, 0.75]]}]}
        with patch("app.service.fx_rates_service.requests.get", return_value=mock_response) as mock_get:
            self.service.get_rates("GBP", "USD")
        called_url = mock_get.call_args[0][0]
        assert "GBP" in called_url
        assert "USD" in called_url

    def test_rate_extracted_from_correct_json_path(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "widget": [{"data": [[None, 42.5]]}]
        }
        with patch("app.service.fx_rates_service.requests.get", return_value=mock_response):
            rate = self.service.get_rates("HKD", "EUR")
        assert rate == 42.5
