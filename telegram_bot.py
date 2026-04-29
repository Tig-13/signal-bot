import html
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CHAT_IDS = [cid.strip() for cid in os.getenv("CHAT_IDS", "").split(",") if cid.strip()]

# DEBUG
print(f"[TELEGRAM DEBUG] TOKEN loaded: {bool(TOKEN)}")
print(f"[TELEGRAM DEBUG] CHAT_ID: {CHAT_ID}")
print(f"[TELEGRAM DEBUG] CHAT_IDS: {CHAT_IDS}")
print(f"[TELEGRAM DEBUG] Number of chat IDs: {len(CHAT_IDS)}")


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    target_ids = CHAT_IDS if CHAT_IDS else ([CHAT_ID] if CHAT_ID else [])

    if not target_ids:
        print("❌ TELEGRAM ERROR: No CHAT_ID or CHAT_IDS configured in .env")
        return

    for chat_id in target_ids:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(url, data=payload, timeout=5)
            result = response.json()
            
            if result.get("ok"):
                print(f"✅ Telegram message sent to {chat_id}")
            else:
                print(f"❌ Telegram ERROR to {chat_id}: {result.get('description', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Telegram EXCEPTION to {chat_id}: {str(e)}")


if __name__ == "__main__":
    send_message("Бот работает ✅")