from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards.main_menu import main_menu
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()


def role_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 Капитан")],
            [KeyboardButton(text="👤 Участник")],
        ],
        resize_keyboard=True,
    )


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
async def process_skills(message: Message, state: FSMContext):
    skills = message.text.strip()
    if not skills:
        await message.answer("Навыки не могут быть пустыми. Введите ваши навыки:")
        return

    await state.update_data(skills=skills)
    await state.set_state(RegistrationState.role)

    await message.answer(
        "Вы хотите быть капитаном или участником?",
        reply_markup=role_keyboard(),
    )


@router.message(RegistrationState.role)
async def process_role(message: Message, state: FSMContext, api):
    text = message.text.lower()

    if "капитан" in text:
        is_kaptain = True
    elif "участник" in text:
        is_kaptain = False
    else:
        await message.answer("Пожалуйста, выберите кнопку.")
        return

    data = await state.get_data()
    telegram_id = message.from_user.id

    try:
        await api.register_user(
            telegram_id=telegram_id,
            full_name=data["full_name"],
            email=data["email"],
            skills=data["skills"],
            is_kaptain=is_kaptain,
        )
    except BackendAPIError as exc:
        await message.answer(f"Ошибка регистрации: {exc.message}")
        return

    await state.clear()

    await message.answer(
        "Вы успешно зарегистрированы",
        reply_markup=main_menu(),
    )