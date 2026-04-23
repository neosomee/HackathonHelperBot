from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()


@router.message(RegistrationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if not full_name:
        await message.answer("ФИО не может быть пустым. Введите ваше ФИО:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationState.email)
    await message.answer("Введите email:")


@router.message(RegistrationState.email)
async def process_email(message: Message, state: FSMContext):
    email = message.text.strip()
    if not email:
        await message.answer("Email не может быть пустым. Введите email:")
        return

    await state.update_data(email=email)
    await state.set_state(RegistrationState.skills)
    await message.answer("Введите ваши навыки:")


@router.message(RegistrationState.skills)
async def process_skills(message: Message, state: FSMContext, api, config):
    skills = message.text.strip()
    if not skills:
        await message.answer("Навыки не могут быть пустыми. Введите ваши навыки:")
        return

    data = await state.get_data()
    telegram_id = message.from_user.id

    try:
        await api.register_user(
            telegram_id=telegram_id,
            full_name=data["full_name"],
            email=data["email"],
            skills=skills,
        )
    except BackendAPIError as exc:
        await message.answer(f"Не удалось зарегистрироваться: {exc.message}")
        return

    await state.clear()
    await message.answer(
        "Вы успешно зарегистрированы",
        reply_markup=main_menu(config.mini_app_url),
    )
