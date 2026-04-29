import requests

OKX_URL = "https://www.okx.com/api/v5/dex/aggregator/quote"


def okx_quote(input_token, output_token, amount):
    params = {
        "chainId": "137",
        "fromTokenAddress": input_token["address"],
        "toTokenAddress": output_token["address"],
        "amount": str(amount),
    }

    response = requests.get(OKX_URL, params=params, timeout=7)

    if response.status_code != 200:
        raise Exception(f"OKX HTTP {response.status_code}")

    data = response.json()

    if "data" not in data or not data["data"]:
        raise Exception(f"OKX error: {data}")

    route = data["data"][0]

    out_amount = int(route["toTokenAmount"])
    gas_usd = float(route.get("estimateGasFee", 0))

    return out_amount, gas_usd