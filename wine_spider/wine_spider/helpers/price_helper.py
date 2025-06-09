import re

def currency_to_symbol(currency):
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
        "AUD": "$",
        "CAD": "$",
        "CHF": "CHF",
        "INR": "₹",
        "RUB": "₽",
    }
    
    return currency_symbols.get(currency, currency)

def symbol_to_currency(symbol):
    symbol_currencies = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "₹": "INR",
        "₽": "RUB",
        "CHF": "CHF",
    }
    
    return symbol_currencies.get(symbol, None)

def remove_commas(value):
    return value.replace(",", "")

def extract_price_range(text: str):
    matches = re.findall(r"[\d,.]+", text)
    if len(matches) >= 2:
        low = float(matches[0].replace(",", ""))
        high = float(matches[1].replace(",", ""))
        return low, high
    return None, None