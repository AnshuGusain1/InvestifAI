import requests
from operator import itemgetter


# replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
url = 'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey=Z9HSD64X49Y6NVTU'
r = requests.get(url)
data = r.json()

print(data)


def sort_by_change_amount(data):
    # Sort top gainers by highest change amount (descending)
    top_gainers = sorted(data['top_gainers'], key=lambda x: float(x['change_amount']), reverse=True)
    print("Top Gainers (Sorted by Change Amount):")
    for gainer in top_gainers:
        print(f"{gainer['ticker']}: Change Amount = {gainer['change_amount']}")
    print("\n")

    # Sort top losers by highest negative change amount (ascending)
    top_losers = sorted(data['top_losers'], key=lambda x: float(x['change_amount']))
    print("Top Losers (Sorted by Change Amount):")
    for loser in top_losers:
        print(f"{loser['ticker']}: Change Amount = {loser['change_amount']}")
    print("\n")

    # Sort most actively traded by highest change amount (descending)
    most_active = sorted(data['most_actively_traded'], key=lambda x: float(x['change_amount']), reverse=True)
    print("Most Actively Traded (Sorted by Change Amount):")
    for active in most_active:
        print(f"{active['ticker']}: Change Amount = {active['change_amount']}")

# Call the function
sort_by_change_amount(data)