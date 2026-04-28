"""Отправка сообщений в Telegram из Django/Celery (HTTP Bot API)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings


def send_telegram_message(chat_id: int, text: str, *, parse_mode: str | None = None) -> bool:
    token = getattr(settings, "BOT_TOKEN", "") or ""
    if not token.strip():
        return False

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return bool(body.get("ok"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return False
