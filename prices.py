import time
import requests
from tokens import TOKENS

def get_prices():
    prices = {}

    url = "https://api.coingecko.com/api/v3/simple/token_price/polygon-pos"

    for token in TOKENS:
        address = token["address"].lower()
        symbol = token["symbol"]

        params = {
            "contract_addresses": address,
            "vs_currencies": "usd",
        }

        response = requests.get(url, params=params, timeout=20)
        data = response.json()

        if address in data and "usd" in data[address]:
            prices[symbol] = data[address]["usd"]
        else:
            print(f"Нет цены CoinGecko для {symbol}: {data}")

        time.sleep(1)

    return prices


if __name__ == "__main__":
    print(get_prices())