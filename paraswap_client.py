import requests

from tokens import CHAIN_ID

PARASWAP_PRICE_URL = "https://api.paraswap.io/prices"


def paraswap_quote(input_token, output_token, amount):
    params = {
        "srcToken": input_token["address"].lower(),
        "destToken": output_token["address"].lower(),
        "amount": str(amount),
        "srcDecimals": input_token["decimals"],
        "destDecimals": output_token["decimals"],
        "side": "SELL",
        "network": CHAIN_ID,
        "version": "5",
    }

    response = requests.get(PARASWAP_PRICE_URL, params=params, timeout=20)
    data = response.json()

    if "priceRoute" not in data:
        raise Exception(f"ParaSwap error: {data}")

    price_route = data["priceRoute"]

    out_amount = int(price_route["destAmount"])

    gas_usd = 0
    if "gasCostUSD" in price_route:
        gas_usd = float(price_route["gasCostUSD"])

    return out_amount, gas_usd