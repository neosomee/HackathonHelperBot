from html import escape

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError

router = Router()


def format_skills(skills_string: str) -> str:
    groups = []

    for chunk in (skills_string or "").split("|"):
        part = chunk.strip()
        if not part:
            continue

        if ":" in part:
            direction, raw_skills = part.split(":", 1)
            skills = [item.strip() for item in raw_skills.split(",") if item.strip()]
        else:
            direction = "Навыки"
            skills = [item.strip() for item in part.split(",") if item.strip()]

        if not skills:
            continue

        skill_lines = "\n".join(f"• {escape(skill)}" for skill in skills)
        groups.append(f"🔹 <b>{escape(direction.strip())}</b>\n{skill_lines}")

    if not groups:
        return "<b>📌 Навыки:</b>\n\n—"

    return "<b>📌 Навыки:</b>\n\n" + "\n\n".join(groups)


def get_membership_info(membership_data: list[dict], telegram_id: int) -> dict:
    memberships = membership_data if isinstance(membership_data, list) else []
    user_memberships = [
        item
        for item in memberships
        if str(item.get("user", {}).get("telegram_id", "")) == str(telegram_id)
    ]

    captain_membership = next(
        (
            item
            for item in user_memberships
            if item.get("status") == "accepted"
            and str(item.get("team", {}).get("captain", {}).get("telegram_id", ""))
            == str(telegram_id)
        ),
        None,
    )
    if captain_membership:
        return {
            "team_name": captain_membership.get("team", {}).get("name") or "—",
        }

    accepted_membership = next(
        (item for item in user_memberships if item.get("status") == "accepted"),
        None,
    )
    if accepted_membership:
        return {
            "team_name": accepted_membership.get("team", {}).get("name") or "—",
        }

    pending_membership = next(
        (item for item in user_memberships if item.get("status") == "pending"),
        None,
    )
    if pending_membership:
        return {
            "team_name": pending_membership.get("team", {}).get("name") or "—",
        }

    return {"team_name": "—"}


def get_role_label(role: str) -> str:
    labels = {
        "CAPTAIN": "Капитан",
        "PARTICIPANT": "Участник",
        "ORGANIZER": "Организатор",
        "ADMIN": "Администратор",
    }
    return labels.get((role or "").upper(), "Участник")


@router.message(F.text == "🚀 Открыть приложение")
async def open_mini_app(message: Message, config):
    if config.mini_app_url:
        await message.answer(
            "Нажмите кнопку «🚀 Открыть приложение» в меню, чтобы открыть Mini App.",
            reply_markup=main_menu(config.mini_app_url),
        )
        return

    await message.answer("Mini App будет подключен позже.")


@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message, api):
    try:
        response = await api.get_profile(message.from_user.id)
    except BackendAPIError as exc:
        if exc.status == 404:
            await message.answer("Профиль не найден. Отправьте /start для регистрации.")
            return
        await message.answer(f"Ошибка backend: {exc.message}")
        return

    membership_info = {"team_name": "—"}
    try:
        membership_data = await api.get_team_members()
        membership_info = get_membership_info(membership_data, message.from_user.id)
    except BackendAPIError:
        pass

    user = response["user"]
    text = "\n\n".join(
        [
            f"<b>👤 ФИО:</b> {escape(user.get('full_name', ''))}",
            f"<b>✉️ Email:</b> {escape(user.get('email', ''))}",
            f"<b>👤 Статус:</b> {escape(get_role_label(user.get('role', '')))}",
            f"<b>👥 Команда:</b> {escape(membership_info['team_name'])}",
            format_skills(user.get("skills", "")),
        ]
    )

    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(F.text == "ℹ️ Помощь")
async def show_help(message: Message):
    await message.answer(
        "Этот бот помогает зарегистрироваться и открыть Mini App. "
        "Создание команд, заявки и основной функционал доступны в приложении."
    )
