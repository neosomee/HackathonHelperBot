from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu_for_user
from bot.services.api import BackendAPIError

router = Router()


@router.message(F.text == "🚀 Открыть приложение")
async def open_mini_app(message: Message, config, api):
    if config.mini_app_url:
        markup = await main_menu_for_user(api, message.from_user.id)
        await message.answer(
            "Нажмите кнопку «🚀 Меню» под полем ввода (Telegram), чтобы открыть Mini App.",
            reply_markup=markup,
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

    user = response["user"]
    await message.answer(
        "\n".join(
            [
                f"ФИО: {user['full_name']}",
                f"Email: {user['email']}",
                f"Навыки: {user['skills']}",
                "Статус команды: доступен в приложении",
            ]
        )
    )


@router.message(F.text == "ℹ️ Помощь")
async def show_help(message: Message):
    await message.answer(
        "Бот: регистрация, Mini App, капитанская панель в приложении.\n\n"
        "Организаторам:\n"
        "• Добавьте свой Telegram ID в ORGANIZER_BOOTSTRAP_TELEGRAM_IDS в .env или назначьте в админке.\n"
        "• «➕ Новый хакатон» — пошаговое создание.\n"
        "• «📊 Выгрузки организатора» — Excel по участникам и командам хакатона.\n\n"
        "Расписание:\n"
        "• «📅 Сейчас в расписании» — текущее и следующее событие по таблице хакатона (Google Sheets).\n"
        "• Напоминания перед событиями обрабатываются в фоне: таблица опрашивается примерно раз в 60 секунд (Celery Beat)."
    )


@router.message(F.text == "📅 Сейчас в расписании")
async def schedule_now_and_next(message: Message, api):
    try:
        data = await api.list_my_schedule_hackathons(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Ошибка backend: {exc.message}")
        return

    items = [
        h
        for h in data.get("hackathons", [])
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
            else "— (нет прошедших/текущих слотов в таблице)"
        )
        nxt_line = (
            f"{nxt.get('title') or '—'} ({nxt.get('start') or '—'})"
            if nxt
            else "— (событий позже нет)"
        )
        parts.append(f"{name}\nСейчас: {cur_line}\nДалее: {nxt_line}")

    await message.answer("\n\n".join(parts))
