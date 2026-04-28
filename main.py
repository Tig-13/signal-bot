import time
import csv
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from tokens import TOKENS, USDC
from odos_client import odos_quote
from zero_x_client import zerox_quote
from paraswap_client import paraswap_quote
from kyberswap_client import kyberswap_quote
from telegram_bot import send_message

CHECK_INTERVAL = 10

TRADE_SIZE_USDC = 10000
SMALL_TEST_USDC = 1000

MIN_NET_DIFF_PERCENT = 0.5
BUY_SLIPPAGE_LIMIT = 2.0
SELL_SLIPPAGE_LIMIT = 2.0

STATS_FILE = "arb_stats.csv"

PLACES = [
    {"name": "Odos", "quote": odos_quote, "link": "https://app.odos.xyz/"},
    {"name": "0x/Matcha", "quote": zerox_quote, "link": "https://matcha.xyz/"},
    {"name": "ParaSwap", "quote": paraswap_quote, "link": "https://app.paraswap.io/"},
    {"name": "KyberSwap", "quote": kyberswap_quote, "link": "https://kyberswap.com/swap/polygon/"},
]

send_message("🤖 Polygon multi-DEX arb bot запущен")


def save_stats(symbol, best_buy, best_sell, backup_sell, buy_slippage, token_amount):
    file_exists = os.path.exists(STATS_FILE)

    with open(STATS_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "time", "token", "volume_usdc",
                "buy_place", "token_amount", "buy_slippage",
                "sell_place", "usdc_back", "sell_slippage",
                "profit_usd", "profit_percent",
                "backup_place", "backup_usdc_back", "backup_profit_percent"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            TRADE_SIZE_USDC,
            best_buy["place"]["name"],
            token_amount,
            round(buy_slippage, 4),
            best_sell["place"]["name"],
            round(best_sell["usdc_back"], 4),
            round(best_sell["sell_slippage"], 4),
            round(best_sell["profit"], 4),
            round(best_sell["profit_percent"], 4),
            backup_sell["place"]["name"],
            round(backup_sell["usdc_back"], 4),
            round(backup_sell["profit_percent"], 4),
        ])


def quote_place(place, input_token, output_token, amount):
    try:
        out_amount, gas_usd = place["quote"](input_token, output_token, amount)
        return {
            "place": place,
            "out_amount": out_amount,
            "gas_usd": gas_usd,
        }
    except Exception as error:
        raise Exception(f"{place['name']}: {error}")


def calc_slippage(small_out, large_out, small_in, large_in):
    small_rate = small_out / small_in
    large_rate = large_out / large_in

    if small_rate <= 0:
        return 999

    return ((small_rate - large_rate) / small_rate) * 100


def parallel_quotes(input_token, output_token, amount, places):
    results = []

    with ThreadPoolExecutor(max_workers=len(places)) as executor:
        futures = [
            executor.submit(quote_place, place, input_token, output_token, amount)
            for place in places
        ]

        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                print("quote error:", error)

    return results


def check_token(token):
    symbol = token["symbol"]
    check_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    large_usdc_amount = int(TRADE_SIZE_USDC * 10 ** USDC["decimals"])
    small_usdc_amount = int(SMALL_TEST_USDC * 10 ** USDC["decimals"])

    # BUY
    buy_quotes = parallel_quotes(USDC, token, large_usdc_amount, PLACES)

    if not buy_quotes:
        return None

    best_buy = max(buy_quotes, key=lambda x: x["out_amount"])

    small_buy_out, _ = best_buy["place"]["quote"](USDC, token, small_usdc_amount)

    buy_slippage = calc_slippage(
        small_buy_out,
        best_buy["out_amount"],
        small_usdc_amount,
        large_usdc_amount,
    )

    if buy_slippage > BUY_SLIPPAGE_LIMIT:
        print(f"{symbol}: skip, buy slippage {buy_slippage:.2f}%")
        return None

    # SELL
    sell_places = [
        place for place in PLACES
        if place["name"] != best_buy["place"]["name"]
    ]

    sell_results = parallel_quotes(token, USDC, best_buy["out_amount"], sell_places)

    if len(sell_results) < 2:
        return None

    half_token_amount = best_buy["out_amount"] // 2

    sell_slippage_results = parallel_quotes(
        token,
        USDC,
        half_token_amount,
        [r["place"] for r in sell_results],
    )

    slippage_map = {
        r["place"]["name"]: r for r in sell_slippage_results
    }

    sell_quotes = []

    for result in sell_results:
        name = result["place"]["name"]

        if name not in slippage_map:
            continue

        half_result = slippage_map[name]

        sell_slippage = calc_slippage(
            half_result["out_amount"],
            result["out_amount"],
            half_token_amount,
            best_buy["out_amount"],
        )

        if sell_slippage > SELL_SLIPPAGE_LIMIT:
            continue

        usdc_back = result["out_amount"] / 10 ** USDC["decimals"]
        total_gas = best_buy["gas_usd"] + result["gas_usd"]

        profit = usdc_back - TRADE_SIZE_USDC - total_gas
        profit_percent = profit / TRADE_SIZE_USDC * 100

        sell_quotes.append({
            "place": result["place"],
            "usdc_back": usdc_back,
            "total_gas": total_gas,
            "profit": profit,
            "profit_percent": profit_percent,
            "sell_slippage": sell_slippage,
        })

    if len(sell_quotes) < 2:
        return None

    sell_quotes.sort(key=lambda x: x["profit_percent"], reverse=True)

    best_sell = sell_quotes[0]
    backup_sell = sell_quotes[1]

    token_amount = best_buy["out_amount"] / 10 ** token["decimals"]

    # сохраняем статистику
    save_stats(symbol, best_buy, best_sell, backup_sell, buy_slippage, token_amount)

    text = (
        f"🔹 TOKEN: {symbol}\n"
        f"{symbol}/USDC\n"
        f"Время: {check_time}\n"
        f"Объём: ${TRADE_SIZE_USDC}\n\n"

        f"1️⃣ Купить: {best_buy['place']['name']}\n"
        f"Получим токенов: {token_amount:.6f}\n"
        f"Buy slippage: {buy_slippage:.2f}%\n"
        f"{best_buy['place']['link']}\n\n"

        f"2️⃣ Продать лучший: {best_sell['place']['name']}\n"
        f"Вернётся: ${best_sell['usdc_back']:.2f}\n"
        f"Sell slippage: {best_sell['sell_slippage']:.2f}%\n"
        f"Профит: {best_sell['profit_percent']:.2f}%\n"
        f"{best_sell['place']['link']}\n\n"

        f"3️⃣ Backup: {backup_sell['place']['name']}\n"
        f"{backup_sell['place']['link']}"
    )

    return text, best_sell["profit_percent"]


while True:
    print("Новая проверка...")

    for token in TOKENS:
        try:
            result = check_token(token)

            if result is None:
                continue

            text, profit_percent = result
            print(text)

            if profit_percent >= MIN_NET_DIFF_PERCENT:
                send_message("🚨 REAL ARB\n" + text)

        except Exception as error:
            print(f"Ошибка по {token['symbol']}:", error)

    print("Пауза...")
    time.sleep(CHECK_INTERVAL)