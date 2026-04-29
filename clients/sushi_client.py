import requests

SUSHI_URL = "https://api.sushi.com/swap/v7/137"
TEST_WALLET = "0x0000000000000000000000000000000000000001"


def sushi_quote(input_token, output_token, amount):
    params = {
        "tokenIn": input_token["address"],
        "tokenOut": output_token["address"],
        "amount": str(amount),
        "sender": TEST_WALLET,
        "maxSlippage": "0.005",
    }

    response = requests.get(SUSHI_URL, params=params, timeout=7)

    if response.status_code != 200:
        raise Exception(f"Sushi HTTP {response.status_code}: {response.text[:150]}")

    data = response.json()

    if data.get("status") != "Success":
        raise Exception(f"Sushi no route: {data}")

    out_amount = int(
        data.get("amountOut")
        or data.get("assumedAmountOut")
        or data.get("route", {}).get("amountOut", 0)
    )

    if out_amount <= 0:
        raise Exception(f"Sushi no amountOut: {data}")

    return out_amount, 0