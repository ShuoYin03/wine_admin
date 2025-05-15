import requests
import json

url = "https://onlineonly.christies.com/sale/searchLots?action=refinecoa&filterids=%7CCountry%2FState%7BFrance%7D%7C&language=en&page=1&saleid=3585&sid&sortby=LotNumber&loadall=true"
# url = "https://onlineonly.christies.com/sale/searchLots?action=paging&language=en&page=1&saleid=3585&sid&sortby=LotNumber&loadall=true"
# general_url = "https://www.christies.com/api/discoverywebsite/auctionpages/lotsearch?action=paging&geocountrycode=GB&language=en&page=1&saleid=29977&salenumber=21934&saletype=Sale&sortby=lotnumber&loadall=true"

# region_url = "https://onlineonly.christies.com/sale/searchLots?action=refinecoa&filterids=%7CRegion%7BBordeaux%7D%7C&language=en&page=1&saleid=1718&saved_lots_only=false&sid&sortby=LotNumber"

# producer_url = "https://onlineonly.christies.com/sale/searchLots?action=refinecoa&filterids=%7CProducer%7BA.H.%20Hirsch%7D%7C&language=en&page=1&saleid=1718&saved_lots_only=false&sid&sortby=LotNumber"

# country_url = "https://onlineonly.christies.com/sale/searchLots?action=refinecoa&filterids=%7CCountry%7BFrance%7D%7C&language=en&page=1&saleid=1718&saved_lots_only=false&sid&sortby=LotNumber"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
}

response = requests.get(url, headers=headers)

print("状态码:", response.status_code)
try:
    data = response.json()
    with open("christies_lots_page_refinecoa.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print("✅ 数据已成功保存为 christies_lots_page_refinecoa.json")
except json.JSONDecodeError:
    print("❌ 响应不是 JSON。返回前1000字:")
    print(response.text[:1000])