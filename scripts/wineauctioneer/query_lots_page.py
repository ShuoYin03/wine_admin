import requests
import json

with open('./wineauctioneer_cookies.json', 'r') as f:
    storage = json.load(f)

cookies_dict = {cookie["name"]: cookie["value"] for cookie in storage.get("cookies", [])}

headers = {
    "Cookie": "; ".join([f"{k}={v}" for k, v in cookies_dict.items()]),
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

url = "https://wineauctioneer.com/wine-auctions/may-2025-auction/lots?items_per_page=32&sort_bef_combine=computed_current_bid_DESC&lots_bottle=All"
response = requests.get(url, headers=headers)

with open("wineauctioneer_may_2025_lots.html", "w", encoding="utf-8") as file:
    file.write(response.text)

print("页面已保存:", response.status_code)
