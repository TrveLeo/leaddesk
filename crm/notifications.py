import httpx

from crm.config import settings


def send_telegram(message: str) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("[notifications] Telegram não configurado — pulando envio.")
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        r = httpx.post(url, json={
            "chat_id": settings.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[notifications] Erro ao enviar Telegram: {e}")
        return False
