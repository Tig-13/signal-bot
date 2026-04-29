import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

QUICKSWAP_ROUTER = Web3.to_checksum_address(
    "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
)

ROUTER_ABI = [
    {
        "name": "getAmountsOut",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "outputs": [
            {"name": "amounts", "type": "uint256[]"},
        ],
    }
]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
router = w3.eth.contract(address=QUICKSWAP_ROUTER, abi=ROUTER_ABI)


def quickswap_quote(input_token, output_token, amount):
    path = [
        Web3.to_checksum_address(input_token["address"]),
        Web3.to_checksum_address(output_token["address"]),
    ]

    try:
        amounts = router.functions.getAmountsOut(int(amount), path).call()
        out_amount = int(amounts[-1])
        gas_usd = 0
        return out_amount, gas_usd

    except Exception as error:
        raise Exception(f"QuickSwap no route: {error}")