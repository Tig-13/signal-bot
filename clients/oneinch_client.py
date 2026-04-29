import os
import requests
from dotenv import load_dotenv

from tokens import CHAIN_ID

load_dotenv()

ONEINCH_API_KEY = os.getenv("ONEINCH_API_KEY")
ONEINCH_URL = f"https://api.1inch.com/swap/v6.1/{CHAIN_ID}/quote"


def oneinch_quote(input_token, output_token, amount):
    if not ONEINCH_API_KEY:
        raise Exception("ONEINCH_API_KEY не найден в .env")

    params = {
        "src": input_token["address"],
        "dst": output_token["address"],
        "amount": str(amount),
        "includeGas": "true",
    }

    headers = {
        "Authorization": f"Bearer {ONEINCH_API_KEY}",
        "Accept": "application/json",
    }

    response = requests.get(ONEINCH_URL, params=params, headers=headers, timeout=7)
    data = response.json()

    if "dstAmount" not in data:
        raise Exception(f"1inch error: {data}")

    out_amount = int(data["dstAmount"])

    gas_usd = 0
    return out_amount, gas_usd