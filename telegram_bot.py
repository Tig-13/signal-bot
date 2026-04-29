import html
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHAT_IDS = [cid.strip() for cid in os.getenv("CHAT_IDS", "").split(",") if cid.strip()]


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    target_ids = CHAT_IDS if CHAT_IDS else ([CHAT_ID] if CHAT_ID else [])

    for chat_id in target_ids:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        response = requests.post(url, data=payload)
        print(response.json())


if __name__ == "__main__":
    send_message("Бот работает ✅")