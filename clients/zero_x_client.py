import os
import requests
from dotenv import load_dotenv
from tokens import CHAIN_ID, USDC, WMATIC
from clients.odos_client import get_token_to_usdc_price

load_dotenv()

ZEROX_API_KEY = os.getenv("ZEROX_API_KEY")
ZEROX_PRICE_URL = "https://api.0x.org/swap/allowance-holder/price"


def get_0x_token_to_usdc_price(token, trade_size_usdc=100):
    amount = trade_size_usdc * 10**6
    # amount = str(1 * 10 ** token["decimals"])

    params = {
        "chainId": CHAIN_ID,
        "sellToken": token["address"],
        "buyToken": USDC["address"],
        "sellAmount": amount,
    }

    headers = {
        "0x-api-key": ZEROX_API_KEY,
        "0x-version": "v2",
    }

    response = requests.get(ZEROX_PRICE_URL, params=params, headers=headers, timeout=7)
    data = response.json()

    if "buyAmount" not in data:
        raise Exception(f"0x error for {token['symbol']}: {data}")

    price = int(data["buyAmount"]) / 10 ** USDC["decimals"]

    gas_usd = 0
    if "gas" in data and "gasPrice" in data:
        gas_matic = int(data["gas"]) * int(data["gasPrice"]) / 10**18
        matic_price, _ = get_token_to_usdc_price(WMATIC)
        gas_usd = gas_matic * matic_price

    return price, gas_usd

def zerox_quote(input_token, output_token, amount):
    params = {
        "chainId": CHAIN_ID,
        "sellToken": input_token["address"],
        "buyToken": output_token["address"],
        "sellAmount": str(amount),
    }

    headers = {
        "0x-api-key": ZEROX_API_KEY,
        "0x-version": "v2",
    }

    response = requests.get(ZEROX_PRICE_URL, params=params, headers=headers, timeout=7)
    data = response.json()

    if "buyAmount" not in data:
        raise Exception(f"0x error: {data}")

    out_amount = int(data["buyAmount"])

    gas_usd = 0
    if "gas" in data and "gasPrice" in data:
        gas_matic = int(data["gas"]) * int(data["gasPrice"]) / 10**18
        matic_price, _ = get_token_to_usdc_price(WMATIC)
        gas_usd = gas_matic * matic_price

    return out_amount, gas_usd