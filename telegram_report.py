import os
import json
from typing import Optional
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# Configuration (from .env file)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
CHAT_ID: str = os.getenv("CHAT_ID", "YOUR_CHAT_ID")


def send_telegram_report(
    report_message: str,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    timeout: int = 10,
) -> bool:
    """Send a text message to a Telegram chat.

    Returns True on success, False on recoverable failure, and raises on
    unexpected network errors.
    """
    if chat_id is None:
        chat_id = CHAT_ID

    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or chat_id == "YOUR_CHAT_ID":
        print("🛑 Configuration Error: Please set a valid BOT_TOKEN and CHAT_ID.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": report_message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, data=payload, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()
        if result.get("ok"):
            print(f"✅ Report sent successfully to chat ID: {chat_id}")
            return True
        else:
            print(f"❌ Telegram API Error: {result.get('description', 'Unknown API Error')}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network/Request Error during Telegram call: {e}")
        raise
    except json.JSONDecodeError as e:
        print("❌ Failed to decode JSON response from Telegram.")
        raise


if __name__ == "__main__":
    report_ = (
        "<b>📈 Günlük Rapor! 📈</b>\n\n"
        "Quiz Dosyası: <code>quiz_01-12-25_49-55.json</code>\n"
        "Quiz Tipi: <code>Sıralı Test Quiz</code>\n"
        "Toplam <code>{}</code> sorudan <code>{}</code> doğru yapıldı.\n"
    ).format(100, 84)

    print("--- Attempting to Send Report ---")
    try:
        send_telegram_report(report_)
    except Exception:
        print("Failed to send report in __main__ mode")
    print("----------------------------------")