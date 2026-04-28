import os
import requests
from tokens import CHAIN_ID

OPENOCEAN_URL = f"https://open-api.openocean.finance/v4/{CHAIN_ID}/quote"


def openocean_quote(input_token, output_token, amount):
    gas_price_wei = os.getenv("POLYGON_GAS_PRICE_WEI", "30000000000")

    params = {
        "inTokenAddress": input_token["address"],
        "outTokenAddress": output_token["address"],
        "amountDecimals": str(amount),
        "gasPriceDecimals": gas_price_wei,
        "slippage": "0.5",
    }

    response = requests.get(OPENOCEAN_URL, params=params, timeout=20)

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        data = response.json()
    except Exception:
        raise Exception(f"OpenOcean returned non-JSON: {response.text[:200]}")

    result = data.get("data", data)

    out_amount = (
        result.get("outAmount")
        or result.get("toAmount")
        or result.get("outAmountDecimals")
    )

    if out_amount is None:
        raise Exception(f"OpenOcean no out amount: {data}")

    return int(out_amount), 0