import json
import os
import urllib.error
import urllib.request
from html import escape


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TG_API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""


def _send_message(chat_id: int, text: str) -> bool:
    if not TG_API_BASE or not chat_id:
        return False

    payload = {
        "chat_id": int(chat_id),
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    req = urllib.request.Request(
        f"{TG_API_BASE}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=7):
            return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
        return False


def _send_message_with_markup_return_id(chat_id: int, text: str, reply_markup: dict):
    if not TG_API_BASE or not chat_id:
        return None

    payload = {
        "chat_id": int(chat_id),
        "text": text[:4096],
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    }

    req = urllib.request.Request(
        f"{TG_API_BASE}/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=7) as response:
            data = json.loads(response.read().decode())
            return data.get("result", {}).get("message_id")
    except Exception:
        return None


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


def notify_team_created(team) -> None:
    _send_message(team.captain.telegram_id, _team_summary(team))


def notify_new_application(application) -> None:
    user = application.user
    team = application.team

    text = (
        f"<b>Новая заявка</b>\n\n"
        f"{escape(user.full_name)}\n"
        f"{escape(user.skills or '—')}\n\n"
        f"<b>{escape(team.name)}</b>\n"
        f"{escape(team.description or '—')}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Принять",
                    "callback_data": f"team_app:accept:{user.telegram_id}:{team.id}",
                },
                {
                    "text": "Отклонить",
                    "callback_data": f"team_app:reject:{user.telegram_id}:{team.id}",
                },
            ]
        ]
    }

    message_id = _send_message_with_markup_return_id(
        team.captain.telegram_id,
        text,
        keyboard,
    )

    if message_id:
        application.telegram_message_id = message_id
        application.save(update_fields=["telegram_message_id"])


def notify_application_result(application, accepted: bool) -> None:
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

def edit_application_message(application, accepted: bool):
    if not application.telegram_message_id:
        return

    status_text = "✅ Принята" if accepted else "❌ Отклонена"

    text = (
        f"<b>Заявка</b>\n\n"
        f"{escape(application.user.full_name)}\n"
        f"{escape(application.user.skills or '—')}\n\n"
        f"<b>{escape(application.team.name)}</b>\n"
        f"\n<b>Статус:</b> {status_text}"
    )

    payload = {
        "chat_id": application.team.captain.telegram_id,
        "message_id": application.telegram_message_id,
        "text": text,
        "parse_mode": "HTML",
    }

    req = urllib.request.Request(
        f"{TG_API_BASE}/editMessageText",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

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


def notify_team_closed_status(team) -> None:
    _send_message(
        team.captain.telegram_id,
        (
            f"📢 <b>Статус набора изменён</b>\n\n"
            f"👥 <b>Команда:</b> {escape(team.name)}\n"
            f"📢 <b>Набор:</b> {'🟢 открыт' if team.is_open else '🔴 закрыт'}"
        ),
    )