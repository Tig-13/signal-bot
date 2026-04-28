import requests
from tokens import CHAIN_ID, USDC

ODOS_QUOTE_URL = "https://api.odos.xyz/sor/quote/v3"


def get_token_to_usdc_price(token, trade_size_usdc=100):
    amount = str(trade_size_usdc * 10**6)
    # amount = str(1 * 10 ** token["decimals"])

    payload = {
        "chainId": CHAIN_ID,
        "inputTokens": [
            {"tokenAddress": token["address"], "amount": amount}
        ],
        "outputTokens": [
            {"tokenAddress": USDC["address"], "proportion": 1}
        ],
        "slippageLimitPercent": 0.5,
    }

    response = requests.post(ODOS_QUOTE_URL, json=payload, timeout=20)
    data = response.json()

    if "outAmounts" not in data:
        raise Exception(f"Odos error for {token['symbol']}: {data}")

    price = int(data["outAmounts"][0]) / 10 ** USDC["decimals"]
    gas_usd = float(data.get("gasEstimateValue", 0))

    return price, gas_usd

def odos_quote(input_token, output_token, amount):
    payload = {
        "chainId": CHAIN_ID,
        "inputTokens": [
            {
                "tokenAddress": input_token["address"],
                "amount": str(amount),
            }
        ],
        "outputTokens": [
            {
                "tokenAddress": output_token["address"],
                "proportion": 1,
            }
        ],
        "slippageLimitPercent": 0.5,
    }

    response = requests.post(ODOS_QUOTE_URL, json=payload, timeout=20)
    data = response.json()

    if "outAmounts" not in data:
        raise Exception(f"Odos error: {data}")

    out_amount = int(data["outAmounts"][0])
    gas_usd = float(data.get("gasEstimateValue", 0))

    return out_amount, gas_usd