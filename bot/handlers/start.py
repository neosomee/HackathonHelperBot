from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, api, config):
    await state.clear()
    telegram_id = message.from_user.id

    try:
        await api.get_profile(telegram_id)
    except BackendAPIError as exc:
        if exc.status == 404:
            await state.set_state(RegistrationState.full_name)
            await message.answer("Добро пожаловать! Введите ваше ФИО:")
            return
        await message.answer(f"Ошибка backend: {exc.message}")
        return

    await message.answer(
        "Вы уже зарегистрированы. Главное меню:",
        reply_markup=main_menu(),
    )