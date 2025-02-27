import yfinance as yf
import requests
from bs4 import BeautifulSoup

news = yf.Search("AAPL", news_count=3)




links = [d['link'] for d in news.news]
#print(links)

url = links[0]
response = requests.get(url)

soup = BeautifulSoup(response.text, 'html.parser')

paragraphs = soup.find_all('p')

for paragraph in paragraphs:
    print(paragraph.text)
    print()