import time
import requests

LIFI_URL = "https://li.quest/v1/quote"
TEST_WALLET = "0x0000000000000000000000000000000000000001"

LAST_REQUEST_TIME = 0
LIFI_DELAY_SECONDS = 3


def wait_lifi_limit():
    global LAST_REQUEST_TIME

    now = time.time()
    diff = now - LAST_REQUEST_TIME

    if diff < LIFI_DELAY_SECONDS:
        time.sleep(LIFI_DELAY_SECONDS - diff)

    LAST_REQUEST_TIME = time.time()


def lifi_quote(input_token, output_token, amount):
    wait_lifi_limit()

    params = {
        "fromChain": 137,
        "toChain": 137,
        "fromToken": input_token["address"].lower(),
        "toToken": output_token["address"].lower(),
        "fromAmount": str(amount),
        "fromAddress": TEST_WALLET,
        "slippage": "0.005",
    }

    response = requests.get(LIFI_URL, params=params, timeout=20)

    if response.status_code == 429:
        raise Exception("rate limit")

    if response.status_code == 404:
        raise Exception("no route / high price impact")

    if response.status_code != 200:
        raise Exception(f"LI.FI HTTP {response.status_code}: {response.text[:150]}")

    data = response.json()

    if "estimate" not in data:
        raise Exception(f"LI.FI error: {data}")

    out_amount = int(data["estimate"]["toAmount"])

    gas_costs = data["estimate"].get("gasCosts", [])
    gas_usd = sum(float(g.get("amountUSD", 0)) for g in gas_costs)

    return out_amount, gas_usd