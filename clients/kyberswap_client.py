import requests

KYBER_CHAIN = "polygon"
KYBER_URL = f"https://aggregator-api.kyberswap.com/{KYBER_CHAIN}/api/v1/routes"


def kyberswap_quote(input_token, output_token, amount):
    params = {
        "tokenIn": input_token["address"],
        "tokenOut": output_token["address"],
        "amountIn": str(amount),
    }

    headers = {
        "x-client-id": "signal-bot",
        "Accept": "application/json",
    }

    response = requests.get(KYBER_URL, params=params, headers=headers, timeout=7)
    data = response.json()

    route_summary = data.get("data", {}).get("routeSummary")

    if not route_summary:
        raise Exception(f"KyberSwap error: {data}")

    out_amount = int(route_summary["amountOut"])
    gas_usd = float(route_summary.get("gasUsd", 0))

    return out_amount, gas_usd