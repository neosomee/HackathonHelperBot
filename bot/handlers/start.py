from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu, main_menu_for_user
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, api, config):
    await state.clear()
    telegram_id = message.from_user.id

    try:
        # Проверяем, зарегистрирован ли пользователь
        await api.get_profile(telegram_id)

    except BackendAPIError as exc:
        if exc.status == 404:
            # Новый пользователь → запускаем регистрацию
            await state.set_state(RegistrationState.full_name)
            await message.answer("Добро пожаловать! Введите ваше ФИО:")
            return

        # Любая другая ошибка backend
        await message.answer(f"Ошибка backend: {exc.message}")
        return

    # Пользователь уже существует → пробуем собрать динамическое меню
    try:
        menu_markup = await main_menu_for_user(api, telegram_id)
    except Exception:
        # fallback если API/меню упало
        menu_markup = main_menu()

    await message.answer(
        "Вы уже зарегистрированы. Главное меню:",
        reply_markup=menu_markup,
    )