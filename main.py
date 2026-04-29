import html
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from tokens import TOKENS, USDC
from telegram_bot import send_message

from clients.odos_client import odos_quote
from clients.zero_x_client import zerox_quote
from clients.kyberswap_client import kyberswap_quote
from clients.quickswap_client import quickswap_quote
from clients.uniswap_v3_client import uniswap_v3_quote
from clients.sushi_client import sushi_quote

from utils.logger import now, log_error, log_debug
from utils.csv_writer import save_row


CHECK_INTERVAL = 10

TRADE_SIZES_USDC = [50, 100, 200, 500]
SMALL_TEST_RATIO = 0.3
MIN_SMALL_TEST_USDC = 20

MIN_NET_DIFF_PERCENT = 0.5
BUY_SLIPPAGE_LIMIT = 3.0
SELL_SLIPPAGE_LIMIT = 3.0

TIMEOUT_PER_DEX = 5
TIMEOUT_TOTAL = 15

TOKEN_WORKERS = 3
STOP_BOT = False

PLACES = [
    {"name": "Odos", "quote": odos_quote, "link": "https://app.odos.xyz/"},
    {"name": "0x/Matcha", "quote": zerox_quote, "link": "https://matcha.xyz/"},
    {"name": "KyberSwap", "quote": kyberswap_quote, "link": "https://kyberswap.com/swap/polygon/"},
    {"name": "QuickSwap", "quote": quickswap_quote, "link": "https://quickswap.exchange/"},
    {"name": "UniswapV3", "quote": uniswap_v3_quote, "link": "https://app.uniswap.org/swap"},
    {"name": "Sushi", "quote": sushi_quote, "link": "https://www.sushi.com/swap"},
]


send_message("🤖 Polygon multi-size arb bot запущен")


def calc_slippage(small_out, large_out, small_in, large_in):
    small_rate = small_out / small_in
    large_rate = large_out / large_in

    if small_rate <= 0:
        return 999

    return ((small_rate - large_rate) / small_rate) * 100


def quote_place(place, input_token, output_token, amount):
    out_amount, gas_usd = place["quote"](input_token, output_token, amount)

    return {
        "place": place,
        "out_amount": int(out_amount),
        "gas_usd": float(gas_usd or 0),
    }


def parallel_quotes(input_token, output_token, amount, places, context=""):
    results = []

    executor = ThreadPoolExecutor(max_workers=len(places))

    try:
        futures = {
            executor.submit(quote_place, place, input_token, output_token, amount): place
            for place in places
        }

        for future in as_completed(futures, timeout=TIMEOUT_TOTAL):
            if STOP_BOT:
                break

            place = futures[future]

            try:
                result = future.result(timeout=TIMEOUT_PER_DEX)
                results.append(result)

                log_debug(
                    f"OK | context={context} | "
                    f"dex={place['name']} | "
                    f"pair={input_token['symbol']}->{output_token['symbol']} | "
                    f"amount_human={amount / 10 ** input_token['decimals']} | "
                    f"out_raw={result['out_amount']}"
                )

            except TimeoutError:
                msg = (
                    f"TIMEOUT | context={context} | "
                    f"dex={place['name']} | "
                    f"pair={input_token['symbol']}->{output_token['symbol']} | "
                    f"amount_human={amount / 10 ** input_token['decimals']}"
                )

                print("quote timeout:", msg)
                log_error(msg)

            except Exception as error:
                msg = (
                    f"context={context} | "
                    f"dex={place['name']} | "
                    f"pair={input_token['symbol']}->{output_token['symbol']} | "
                    f"amount_raw={amount} | "
                    f"amount_human={amount / 10 ** input_token['decimals']} | "
                    f"error={repr(error)}"
                )

                print("quote error:", msg)
                log_error(msg)

    except TimeoutError:
        print(f"Total timeout for {context}")
        log_error(f"TOTAL_TIMEOUT | context={context}")

    except KeyboardInterrupt:
        executor.shutdown(wait=False, cancel_futures=True)
        raise

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return results


def check_token_size(token, trade_size_usdc):
    if STOP_BOT:
        return None

    symbol = token["symbol"]
    check_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    large_usdc_amount = int(trade_size_usdc * 10 ** USDC["decimals"])
    small_test_usdc = max(MIN_SMALL_TEST_USDC, trade_size_usdc * SMALL_TEST_RATIO)
    small_usdc_amount = int(small_test_usdc * 10 ** USDC["decimals"])

    buy_quotes = parallel_quotes(
        USDC,
        token,
        large_usdc_amount,
        PLACES,
        context=f"BUY {symbol} size={trade_size_usdc}",
    )

    if not buy_quotes:
        save_row({
            "time": now(),
            "token": symbol,
            "status": "skipped",
            "reason": "no_buy_quotes",
            "volume_usdc": trade_size_usdc,
            "small_test_usdc": small_test_usdc,
            "buy_dexes_checked": 0,
        })
        return None

    best_buy = max(buy_quotes, key=lambda x: x["out_amount"])
    token_amount = best_buy["out_amount"] / 10 ** token["decimals"]

    try:
        small_buy_out, _ = best_buy["place"]["quote"](USDC, token, small_usdc_amount)
    except Exception as error:
        log_error(
            f"{symbol} buy_slippage_error | "
            f"size={trade_size_usdc} | "
            f"dex={best_buy['place']['name']} | "
            f"error={repr(error)}"
        )

        save_row({
            "time": now(),
            "token": symbol,
            "status": "skipped",
            "reason": f"buy_slippage_error: {error}",
            "volume_usdc": trade_size_usdc,
            "small_test_usdc": small_test_usdc,
            "buy_place": best_buy["place"]["name"],
            "token_amount": token_amount,
            "buy_dexes_checked": len(buy_quotes),
        })
        return None

    buy_slippage = calc_slippage(
        small_buy_out,
        best_buy["out_amount"],
        small_usdc_amount,
        large_usdc_amount,
    )

    if buy_slippage > BUY_SLIPPAGE_LIMIT:
        save_row({
            "time": now(),
            "token": symbol,
            "status": "skipped",
            "reason": "high_buy_slippage",
            "volume_usdc": trade_size_usdc,
            "small_test_usdc": small_test_usdc,
            "buy_place": best_buy["place"]["name"],
            "token_amount": token_amount,
            "buy_slippage": round(buy_slippage, 4),
            "buy_dexes_checked": len(buy_quotes),
        })
        return None

    sell_places = [
        place for place in PLACES
        if place["name"] != best_buy["place"]["name"]
    ]

    sell_results = parallel_quotes(
        token,
        USDC,
        best_buy["out_amount"],
        sell_places,
        context=f"SELL {symbol} size={trade_size_usdc}",
    )

    if len(sell_results) < 2:
        save_row({
            "time": now(),
            "token": symbol,
            "status": "skipped",
            "reason": "not_enough_sell_quotes",
            "volume_usdc": trade_size_usdc,
            "small_test_usdc": small_test_usdc,
            "buy_place": best_buy["place"]["name"],
            "token_amount": token_amount,
            "buy_slippage": round(buy_slippage, 4),
            "buy_dexes_checked": len(buy_quotes),
            "sell_dexes_checked": len(sell_results),
        })
        return None

    half_token_amount = best_buy["out_amount"] // 2

    sell_slippage_results = parallel_quotes(
        token,
        USDC,
        half_token_amount,
        [r["place"] for r in sell_results],
        context=f"SELL_SLIPPAGE {symbol} size={trade_size_usdc}",
    )

    slippage_map = {
        r["place"]["name"]: r
        for r in sell_slippage_results
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

        profit = usdc_back - trade_size_usdc - total_gas
        profit_percent = profit / trade_size_usdc * 100

        sell_quotes.append({
            "place": result["place"],
            "usdc_back": usdc_back,
            "total_gas": total_gas,
            "profit": profit,
            "profit_percent": profit_percent,
            "sell_slippage": sell_slippage,
        })

    if len(sell_quotes) < 2:
        save_row({
            "time": now(),
            "token": symbol,
            "status": "skipped",
            "reason": "sell_slippage_filtered_all",
            "volume_usdc": trade_size_usdc,
            "small_test_usdc": small_test_usdc,
            "buy_place": best_buy["place"]["name"],
            "token_amount": token_amount,
            "buy_slippage": round(buy_slippage, 4),
            "buy_dexes_checked": len(buy_quotes),
            "sell_dexes_checked": len(sell_results),
        })
        return None

    sell_quotes.sort(key=lambda x: x["profit_percent"], reverse=True)

    best_sell = sell_quotes[0]
    backup_sell = sell_quotes[1]

    spread_percent = (
        (best_sell["usdc_back"] - trade_size_usdc)
        / trade_size_usdc
        * 100
    )

    route_pair = f"{best_buy['place']['name']} -> {best_sell['place']['name']}"
    is_near_profit = best_sell["profit_percent"] >= -0.05

    save_row({
        "time": now(),
        "token": symbol,
        "status": "ok",
        "reason": "",
        "volume_usdc": trade_size_usdc,
        "small_test_usdc": small_test_usdc,

        "usdc_back": round(best_sell["usdc_back"], 4),
        "backup_usdc_back": round(backup_sell["usdc_back"], 4),
        "profit_usd": round(best_sell["profit"], 4),
        "profit_percent": round(best_sell["profit_percent"], 4),
        "backup_profit_percent": round(backup_sell["profit_percent"], 4),

        "buy_place": best_buy["place"]["name"],
        "sell_place": best_sell["place"]["name"],
        "backup_place": backup_sell["place"]["name"],
        "token_amount": token_amount,
        "buy_slippage": round(buy_slippage, 4),
        "sell_slippage": round(best_sell["sell_slippage"], 4),
        "spread_percent": round(spread_percent, 4),
        "route_pair": route_pair,
        "is_near_profit": is_near_profit,
        "buy_dexes_checked": len(buy_quotes),
        "sell_dexes_checked": len(sell_results),
    })

    highlight = "<b>🔥 HIGH PROFIT</b>\n" if best_sell['profit_percent'] > 0.9 else ""

    text = (
        f"{highlight}🔹 TOKEN: <b>{html.escape(symbol)}</b>\n"
        f"<b>{html.escape(symbol)}</b>/USDC\n"
        f"Время: {html.escape(check_time)}\n"
        f"Объём: <b>${trade_size_usdc:.2f}</b>\n\n"
        f"1️⃣ Купить: {html.escape(best_buy['place']['name'])}\n"
        f"Получим токенов: <b>{token_amount:.6f} {html.escape(symbol)}</b>\n"
        f"Buy slippage: {buy_slippage:.2f}%\n"
        f"{html.escape(best_buy['place']['link'])}\n\n"
        f"2️⃣ Продать лучший: {html.escape(best_sell['place']['name'])}\n"
        f"Вернётся: <b>${best_sell['usdc_back']:.2f}</b>\n"
        f"Sell slippage: {best_sell['sell_slippage']:.2f}%\n"
        f"Профит: <b>${best_sell['profit']:.2f}</b>\n"
        f"Профит: {best_sell['profit_percent']:.2f}%\n"
        f"{html.escape(best_sell['place']['link'])}\n\n"
        f"3️⃣ Backup: {html.escape(backup_sell['place']['name'])}\n"
        f"Вернётся: <b>${backup_sell['usdc_back']:.2f}</b>\n"
        f"Профит: {backup_sell['profit_percent']:.2f}%\n"
        f"{html.escape(backup_sell['place']['link'])}"
    )

    return text, best_sell["profit_percent"]


def check_token_all_sizes(token):
    results = []

    for trade_size in TRADE_SIZES_USDC:
        if STOP_BOT:
            break

        result = check_token_size(token, trade_size)

        if result is not None:
            results.append(result)

    return results


try:
    while not STOP_BOT:
        print("Новая проверка...")

        executor = ThreadPoolExecutor(max_workers=TOKEN_WORKERS)

        try:
            futures = {
                executor.submit(check_token_all_sizes, token): token
                for token in TOKENS
            }

            for future in as_completed(futures):
                if STOP_BOT:
                    break

                token = futures[future]

                try:
                    results = future.result()

                    for text, profit_percent in results:
                        print(text)

                        if profit_percent >= MIN_NET_DIFF_PERCENT:
                            send_message("🚨 REAL ARB\n" + text)

                except Exception as error:
                    print(f"Ошибка по {token['symbol']}:", error)
                    log_error(f"MAIN token={token['symbol']} | error={repr(error)}")

                    save_row({
                        "time": now(),
                        "token": token["symbol"],
                        "status": "error",
                        "reason": str(error),
                    })

        except KeyboardInterrupt:
            STOP_BOT = True
            print("\n⛔ Останавливаю бота...")
            log_error("Bot stopping by Ctrl+C")
            executor.shutdown(wait=False, cancel_futures=True)
            break

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        print("Пауза...")

        for _ in range(CHECK_INTERVAL):
            if STOP_BOT:
                break
            time.sleep(1)

except KeyboardInterrupt:
    STOP_BOT = True
    print("\n⛔ Бот остановлен пользователем Ctrl+C")
    log_error("Bot stopped by user")

print("✅ Завершено")