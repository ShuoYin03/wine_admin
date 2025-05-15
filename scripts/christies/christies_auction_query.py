import requests
import demjson3
import re
import json

url = f"https://www.christies.com/en/results?year=2007&filters=|category_14|&month=4"

response = requests.get(url)
match = re.search(r'window\.chrComponents\.calendar\s*=\s*({.*?});\s*\n', response.text, re.DOTALL)

data = demjson3.decode(match.group(1))
events = data.get('data', {}).get('events', [])

with open('christies_all_auction_response.json', 'w') as f:
    json.dump(data, f, indent=4)