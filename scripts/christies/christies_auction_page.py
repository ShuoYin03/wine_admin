import requests

url = "https://onlineonly.christies.com/s/wine-spirits-online-nyc/lots/1718?filters=%7CVintage%7B2010%20-%20Present%7D%7C&page=1&sortby=LotNumber"

response = requests.get(url)
print("状态码:", response.status_code)
with open("christies_auction_page.html", "w", encoding="utf-8") as f:
    f.write(response.text)
    print("✅ 数据已成功保存为 christies_auction_page.html")