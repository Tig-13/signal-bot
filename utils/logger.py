import os
from datetime import datetime

LOG_DIR = "logs"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def get_error_log_file():
    ensure_log_dir()
    return os.path.join(LOG_DIR, f"errors_{today()}.txt")


def get_debug_log_file():
    ensure_log_dir()
    return os.path.join(LOG_DIR, f"debug_{today()}.txt")


def log_error(message):
    with open(get_error_log_file(), "a", encoding="utf-8") as file:
        file.write(f"[{now()}] {message}\n")


def log_debug(message):
    with open(get_debug_log_file(), "a", encoding="utf-8") as file:
        file.write(f"[{now()}] {message}\n")