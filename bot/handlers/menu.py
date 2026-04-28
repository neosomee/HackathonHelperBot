from html import escape

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError

router = Router()


def _extract_list(data) -> list:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("hackathons", "team_members", "memberships", "requests", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value

    return []


def format_skills(skills_string: str) -> str:
    groups = []

    for chunk in (skills_string or "").split("|"):
        part = chunk.strip()
        if not part:
            continue

        if ":" in part:
            direction, raw_skills = part.split(":", 1)
            direction = direction.strip()
            skills = [item.strip() for item in raw_skills.split(",") if item.strip()]
        else:
            direction = "Навыки"
            skills = [item.strip() for item in part.split(",") if item.strip()]

        if not skills:
            continue

        skill_lines = "\n".join(f"• {escape(skill)}" for skill in skills)
        groups.append(f"🔹 <b>{escape(direction)}</b>\n{skill_lines}")

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
            and str(item.get("team", {}).get("captain", {}).get("telegram_id", "")) == str(telegram_id)
        ),
        None,
    )
    if captain_membership:
        return {
            "team_name": captain_membership.get("team", {}).get("name") or "—",
            "status": "Капитан",
        }

    accepted_membership = next(
        (item for item in user_memberships if item.get("status") == "accepted"),
        None,
    )
    if accepted_membership:
        return {
            "team_name": accepted_membership.get("team", {}).get("name") or "—",
            "status": "Участник",
        }

    pending_membership = next(
        (item for item in user_memberships if item.get("status") == "pending"),
        None,
    )
    if pending_membership:
        return {
            "team_name": pending_membership.get("team", {}).get("name") or "—",
            "status": "Заявка отправлена",
        }

    return {
        "team_name": "—",
        "status": "Без команды",
    }


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
            "Нажмите кнопку в меню, чтобы открыть Mini App.",
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

    user = response.get("user", {})
    membership_info = {"team_name": "—", "status": "Без команды"}

    try:
        if hasattr(api, "list_team_members"):
            data = await api.list_team_members()
        elif hasattr(api, "get_team_members"):
            data = await api.get_team_members()
        else:
            data = []
        memberships = _extract_list(data)
        membership_info = get_membership_info(memberships, message.from_user.id)
    except BackendAPIError:
        pass

    text = "\n\n".join(
        [
            f"<b>👤 ФИО:</b> {escape(user.get('full_name', ''))}",
            f"<b>✉️ Email:</b> {escape(user.get('email', ''))}",
            f"<b>👑 Статус:</b> {escape(get_role_label(user.get('role', '')))}",
            f"<b>👥 Команда:</b> {escape(membership_info['team_name'])}",
            f"<b>📌 Статус команды:</b> {escape(membership_info['status'])}",
            format_skills(user.get("skills", "")),
        ]
    )

    await message.answer(text, parse_mode=ParseMode.HTML)


@router.message(F.text == "📅 Сейчас в расписании")
async def schedule_now_and_next(message: Message, api):
    try:
        data = await api.list_my_schedule_hackathons(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Ошибка backend: {exc.message}")
        return

    items = [
        h
        for h in _extract_list(data)
        if (h.get("schedule_sheet_url") or "").strip()
    ]

    if not items:
        await message.answer(
            "Нет хакатонов с подключённым расписанием, где вы состоите в зачисленной команде. "
            "Подключение команды к событию — у капитана в Mini App."
        )
        return

    parts = []
    for h in items:
        try:
            st = await api.get_hackathon_schedule_status(h["id"], message.from_user.id)
        except BackendAPIError as exc:
            parts.append(f"{h.get('name', 'Хакатон')}: не удалось загрузить расписание ({exc.message})")
            continue

        cur = st.get("current") or {}
        nxt = st.get("next") or {}
        name = st.get("hackathon_name") or h.get("name") or "Хакатон"

        cur_line = (
            f"{cur.get('title') or '—'} ({cur.get('start') or '—'})"
            if cur
            else "— (нет текущих событий)"
        )
        nxt_line = (
            f"{nxt.get('title') or '—'} ({nxt.get('start') or '—'})"
            if nxt
            else "— (следующих событий нет)"
        )

        parts.append(f"{name}\nСейчас: {cur_line}\nДалее: {nxt_line}")

    await message.answer("\n\n".join(parts))


@router.message(F.text == "ℹ️ Помощь")
async def show_help(message: Message):
    await message.answer(
        "Бот помогает зарегистрироваться, открыть Mini App и смотреть профиль.\n\n"
        "Команды, заявки и панель капитана доступны в приложении.\n"
        "Расписание хакатона можно смотреть отдельно, если оно подключено."
    )