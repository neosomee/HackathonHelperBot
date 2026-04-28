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
        "• «📊 Выгрузки организатора» — Excel по участникам и командам хакатона."
    )
