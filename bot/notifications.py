"""Telegram notifications for the Django backend.

Used for:
- team creation
- new applications
- application results
- captain transfer
- team deletion
- member leaving
- team open/close status
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from html import escape
from typing import Any, Optional

from django.conf import settings


BOT_TOKEN = getattr(settings, "BOT_TOKEN", "") or os.getenv("BOT_TOKEN", "")
TG_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""


def _request_json(url: str, payload: dict[str, Any], timeout: int = 7) -> Optional[dict[str, Any]]:
    if not TG_API_BASE:
        return None

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return None


def send_telegram_message(chat_id: int, text: str, *, parse_mode: str | None = None) -> bool:
    token = getattr(settings, "BOT_TOKEN", "") or ""
    if not token.strip():
        return False

    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": int(chat_id),
        "text": text[:4096],
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    result = _request_json(url, payload, timeout=15)
    return bool(result and result.get("ok"))


def _send_message(chat_id: int, text: str) -> bool:
    if not TG_API_BASE or not chat_id:
        return False

    payload = {
        "chat_id": int(chat_id),
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    result = _request_json(f"{TG_API_BASE}/sendMessage", payload, timeout=7)
    return bool(result and result.get("ok"))


def _send_message_with_markup_return_id(chat_id: int, text: str, reply_markup: dict[str, Any]) -> Optional[int]:
    if not TG_API_BASE or not chat_id:
        return None

    payload = {
        "chat_id": int(chat_id),
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup,
    }

    result = _request_json(f"{TG_API_BASE}/sendMessage", payload, timeout=7)
    if not result or not result.get("ok"):
        return None

    return result.get("result", {}).get("message_id")


def _edit_message_text(
    chat_id: int,
    message_id: int,
    text: str,
    *,
    reply_markup: Optional[dict[str, Any]] = None,
) -> bool:
    if not TG_API_BASE or not chat_id or not message_id:
        return False

    payload: dict[str, Any] = {
        "chat_id": int(chat_id),
        "message_id": int(message_id),
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    result = _request_json(f"{TG_API_BASE}/editMessageText", payload, timeout=7)
    return bool(result and result.get("ok"))


def _team_summary(team) -> str:
    return (
        f"🚀 <b>Команда создана</b>\n\n"
        f"🏷 <b>{escape(team.name)}</b>\n"
        f"📝 {escape(team.description or '—')}\n\n"
        f"🛠 <b>Стек:</b> {escape(team.tech_stack or '—')}\n"
        f"👥 <b>Вакансии:</b> {escape(team.vacancies or '—')}\n"
        f"📊 <b>Лимит:</b> {team.max_members}\n"
        f"📢 <b>Набор:</b> {'🟢 открыт' if team.is_open else '🔴 закрыт'}"
    )


def _application_text(application, *, status_line: str | None = None) -> str:
    user = application.user
    team = application.team

    text = (
        f"📩 <b>Новая заявка в команду</b>\n\n"
        f"👤 <b>Участник:</b> {escape(user.full_name)}\n"
        f"📧 <b>Email:</b> {escape(user.email or '—')}\n"
        f"🛠 <b>Навыки:</b> {escape(user.skills or '—')}\n\n"
        f"👥 <b>Команда:</b> {escape(team.name)}\n"
        f"📝 <b>Описание:</b> {escape(team.description or '—')}\n"
        f"🧩 <b>Стек:</b> {escape(team.tech_stack or '—')}\n"
        f"📌 <b>Вакансии:</b> {escape(team.vacancies or '—')}\n"
        f"📊 <b>Лимит:</b> {team.max_members}\n"
        f"📢 <b>Набор:</b> {'🟢 открыт' if team.is_open else '🔴 закрыт'}"
    )
    if status_line:
        text += f"\n\n<b>Статус:</b> {status_line}"
    return text


def notify_team_created(team) -> None:
    _send_message(team.captain.telegram_id, _team_summary(team))


def notify_team_closed_status(team) -> None:
    _send_message(
        team.captain.telegram_id,
        (
            f"📢 <b>Статус набора изменён</b>\n\n"
            f"👥 <b>Команда:</b> {escape(team.name)}\n"
            f"📢 <b>Набор:</b> {'🟢 открыт' if team.is_open else '🔴 закрыт'}"
        ),
    )


def notify_new_application(application) -> None:
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Принять",
                    "callback_data": f"team_app:accept:{application.user.telegram_id}:{application.team.id}",
                },
                {
                    "text": "Отклонить",
                    "callback_data": f"team_app:reject:{application.user.telegram_id}:{application.team.id}",
                },
            ]
        ]
    }

    message_id = _send_message_with_markup_return_id(
        application.team.captain.telegram_id,
        _application_text(application),
        keyboard,
    )

    if message_id:
        application.telegram_message_id = message_id
        application.save(update_fields=["telegram_message_id"])


def edit_application_message(application, accepted: bool) -> None:
    if not application.telegram_message_id:
        return

    status_line = "✅ принят" if accepted else "❌ отклонён"

    _edit_message_text(
        application.team.captain.telegram_id,
        application.telegram_message_id,
        _application_text(application, status_line=status_line),
        reply_markup={"inline_keyboard": []},
    )


def notify_application_result(application, accepted: bool) -> None:
    edit_application_message(application, accepted)

    text = (
        f"✅ <b>Заявка принята</b>\n\n"
        if accepted
        else
        f"❌ <b>Заявка отклонена</b>\n\n"
    )
    text += (
        f"👥 <b>Команда:</b> {escape(application.team.name)}\n"
        f"👤 <b>Участник:</b> {escape(application.user.full_name)}\n"
        f"🛠 <b>Навыки:</b> {escape(application.user.skills or '—')}"
    )
    _send_message(application.user.telegram_id, text)


def notify_captain_transferred(team, old_captain, new_captain) -> None:
    _send_message(
        old_captain.telegram_id,
        (
            f"🔁 <b>Капитанство передано</b>\n\n"
            f"👥 <b>Команда:</b> {escape(team.name)}\n"
            f"👤 <b>Новый капитан:</b> {escape(new_captain.full_name)}"
        ),
    )
    _send_message(
        new_captain.telegram_id,
        (
            f"👑 <b>Вы стали капитаном</b>\n\n"
            f"👥 <b>Команда:</b> {escape(team.name)}"
        ),
    )


def notify_team_deleted(team, members) -> None:
    message = (
        f"🗑 <b>Команда удалена</b>\n\n"
        f"👥 <b>Команда:</b> {escape(team.name)}\n"
        f"📝 <b>Описание:</b> {escape(team.description or '—')}\n"
        f"🧩 <b>Стек:</b> {escape(team.tech_stack or '—')}\n"
        f"📌 <b>Вакансии:</b> {escape(team.vacancies or '—')}\n"
        f"📊 <b>Лимит:</b> {team.max_members}"
    )

    for membership in members:
        _send_message(membership.user.telegram_id, message)


def notify_member_left(team, left_user, members) -> None:
    message = (
        f"👋 <b>Участник вышел из команды</b>\n\n"
        f"👥 <b>Команда:</b> {escape(team.name)}\n"
        f"👤 <b>Участник:</b> {escape(left_user.full_name)}"
    )

    for membership in members:
        if membership.user_id != left_user.id:
            _send_message(membership.user.telegram_id, message)