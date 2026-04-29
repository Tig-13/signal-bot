import csv
import os
from datetime import datetime

LOG_DIR = "logs"

COLUMNS = [
    "time", "token", "status", "reason",
    "volume_usdc", "small_test_usdc",

    "usdc_back", "backup_usdc_back",
    "profit_usd", "profit_percent", "backup_profit_percent",

    "buy_place", "sell_place", "backup_place",
    "token_amount",
    "buy_slippage", "sell_slippage",
    "spread_percent",
    "route_pair",
    "is_near_profit",
    "buy_dexes_checked", "sell_dexes_checked",
]


def today():
    return datetime.now().strftime("%Y-%m-%d")


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def get_stats_file():
    ensure_log_dir()
    return os.path.join(LOG_DIR, f"arb_stats_{today()}.csv")


def save_row(row):
    stats_file = get_stats_file()
    file_exists = os.path.exists(stats_file)

    with open(stats_file, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)

        if not file_exists:
            writer.writeheader()

        writer.writerow({col: row.get(col, "") for col in COLUMNS})