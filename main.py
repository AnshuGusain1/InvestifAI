import requests
from datetime import date

API_KEY = open('API_key.txt').read()
SEARCH_ENGINE_ID = open('SEARCH_ENGINE_ID').read()

search_query = input("Enter search query: ")

url = 'https://www.googleapis.com/customsearch/v1'
params = {
    'key': API_KEY,
    'cx': SEARCH_ENGINE_ID,
    'q': search_query,
    'dateRestrict': '2025-02-10:' + str(date.today().strftime("%Y-%m-%d")),
}

response = requests.get(url, params=params)
results = response.json()['items']
print(results)

for item in results:
    print(item['link'])