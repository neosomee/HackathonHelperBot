from aiogram import F, Router
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError

router = Router()


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
        "Этот бот помогает зарегистрироваться и открыть Mini App. "
        "Создание команд, заявки и основной функционал доступны в приложении."
    )
