import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("POLYGON_RPC_URL", "https://polygon-bor-rpc.publicnode.com")

UNISWAP_QUOTER_V2 = Web3.to_checksum_address(
    "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"
)

QUOTER_ABI = [{
    "name": "quoteExactInputSingle",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [{
        "components": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "amountIn", "type": "uint256"},
            {"name": "fee", "type": "uint24"},
            {"name": "sqrtPriceLimitX96", "type": "uint160"},
        ],
        "name": "params",
        "type": "tuple",
    }],
    "outputs": [
        {"name": "amountOut", "type": "uint256"},
        {"name": "sqrtPriceX96After", "type": "uint160"},
        {"name": "initializedTicksCrossed", "type": "uint32"},
        {"name": "gasEstimate", "type": "uint256"},
    ],
}]

w3 = Web3(Web3.HTTPProvider(RPC_URL))
quoter = w3.eth.contract(address=UNISWAP_QUOTER_V2, abi=QUOTER_ABI)

FEES = [500, 3000, 10000]


def uniswap_v3_quote(input_token, output_token, amount):
    best_out = 0

    for fee in FEES:
        try:
            params = (
                Web3.to_checksum_address(input_token["address"]),
                Web3.to_checksum_address(output_token["address"]),
                int(amount),
                fee,
                0,
            )

            result = quoter.functions.quoteExactInputSingle(params).call()
            out_amount = int(result[0])

            if out_amount > best_out:
                best_out = out_amount

        except Exception:
            continue

    if best_out <= 0:
        raise Exception("UniswapV3 no route")

    return best_out, 0