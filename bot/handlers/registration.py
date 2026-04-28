from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards.main_menu import main_menu_for_user
from bot.services.api import BackendAPIError
from bot.states.registration import RegistrationState

router = Router()


def role_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Участник"),
                KeyboardButton(text="👑 Капитан"),
            ],
            [
                KeyboardButton(text="📋 Организатор"),
                KeyboardButton(text="👑 Капитан + организатор"),
            ],
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
        "Выберите роль (можно комбинировать капитана и организатора отдельной кнопкой):",
        reply_markup=role_keyboard(),
    )


@router.message(RegistrationState.role)
async def process_role(message: Message, state: FSMContext, api):
    text = (message.text or "").lower()

    is_kaptain = False
    can_create_hackathons = False

    if "капитан" in text and "организатор" in text:
        is_kaptain = True
        can_create_hackathons = True
    elif "организатор" in text:
        can_create_hackathons = True
    elif "капитан" in text:
        is_kaptain = True
    elif "участник" in text:
        pass
    else:
        await message.answer("Пожалуйста, выберите одну из кнопок.")
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
            can_create_hackathons=can_create_hackathons,
        )
    except BackendAPIError as exc:
        await message.answer(f"Ошибка регистрации: {exc.message}")
        return

    await state.clear()

    menu_markup = await main_menu_for_user(api, telegram_id)
    extra = ""
    if can_create_hackathons:
        extra = "\n\nВы можете создавать хакатоны (Mini App / бот «➕ Новый хакатон»)."
    await message.answer(
        "Вы успешно зарегистрированы." + extra,
        reply_markup=menu_markup,
    )
