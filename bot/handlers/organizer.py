from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from bot.keyboards.main_menu import main_menu, main_menu_for_user
from bot.services.api import BackendAPIError
from bot.states.hackathon_create import HackathonCreateState

router = Router()


# ======================
# helpers
# ======================

async def safe_menu(api, telegram_id: int):
    try:
        return await main_menu_for_user(api, telegram_id)
    except Exception:
        return main_menu()


def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Набор открыт"), KeyboardButton(text="⛔ Набор закрыт")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


async def handle_cancel(message: Message, state: FSMContext, api):
    await state.clear()
    markup = await safe_menu(api, message.from_user.id)
    await message.answer("Отменено.", reply_markup=markup)


# ======================
# callbacks
# ======================

class HackathonPickCallback(CallbackData, prefix="org_h"):
    hackathon_id: int


class ExportKindCallback(CallbackData, prefix="org_x"):
    hackathon_id: int
    kind: str


# ======================
# создание хакатона
# ======================

@router.message(F.text == "➕ Новый хакатон")
async def hackathon_create_entry(message: Message, state: FSMContext, api):
    try:
        perm = await api.get_hackathon_permissions(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Не удалось проверить права: {exc.message}")
        return

    if not perm.get("can_create_hackathon"):
        await message.answer(
            "Нет доступа к созданию хакатонов.\n\n"
            "Добавь свой Telegram ID в ORGANIZER_BOOTSTRAP_TELEGRAM_IDS или через Django Admin."
        )
        return

    await state.set_state(HackathonCreateState.name)
    await message.answer("Введите название хакатона:", reply_markup=cancel_kb())


@router.message(StateFilter(HackathonCreateState.name))
async def hackathon_create_name(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()

    if text == "❌ Отмена":
        return await handle_cancel(message, state, api)

    if not text:
        await message.answer("Название не может быть пустым.")
        return

    await state.update_data(name=text)
    await state.set_state(HackathonCreateState.description)

    await message.answer("Описание (или «-»):", reply_markup=cancel_kb())


@router.message(StateFilter(HackathonCreateState.description))
async def hackathon_create_description(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()

    if text == "❌ Отмена":
        return await handle_cancel(message, state, api)

    await state.update_data(description="" if text == "-" else text)
    await state.set_state(HackathonCreateState.schedule_url)

    await message.answer("Ссылка на расписание (или «-»):", reply_markup=cancel_kb())


@router.message(StateFilter(HackathonCreateState.schedule_url))
async def hackathon_create_schedule(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()

    if text == "❌ Отмена":
        return await handle_cancel(message, state, api)

    await state.update_data(schedule_sheet_url="" if text == "-" else text)
    await state.set_state(HackathonCreateState.recruitment_open)

    await message.answer(
        "Открыт ли набор команд?",
        reply_markup=yes_no_kb(),
    )


@router.message(StateFilter(HackathonCreateState.recruitment_open))
async def hackathon_create_recruitment(message: Message, state: FSMContext, api):
    text = (message.text or "").lower()

    if "❌" in text:
        return await handle_cancel(message, state, api)

    if "открыт" in text:
        is_open = True
    elif "закрыт" in text:
        is_open = False
    else:
        await message.answer("Выберите кнопку.")
        return

    data = await state.get_data()
    await state.clear()

    try:
        result = await api.create_hackathon(
            telegram_id=message.from_user.id,
            name=data["name"],
            description=data.get("description", ""),
            schedule_sheet_url=data.get("schedule_sheet_url", ""),
            is_team_join_open=is_open,
        )
    except BackendAPIError as exc:
        markup = await safe_menu(api, message.from_user.id)
        await message.answer(f"Ошибка: {exc.message}", reply_markup=markup)
        return

    h = result.get("hackathon", {})
    markup = await safe_menu(api, message.from_user.id)

    await message.answer(
        f"✅ Хакатон создан\n\n"
        f"{h.get('name')}\n"
        f"id: {h.get('id')}",
        reply_markup=markup,
    )


# ======================
# выгрузки
# ======================

@router.message(F.text == "📊 Выгрузки организатора")
async def organizer_entry(message: Message, api):
    try:
        data = await api.get_organized_hackathons(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Ошибка: {exc.message}")
        return

    hacks = data.get("hackathons") or []

    if not hacks:
        await message.answer("Нет доступных хакатонов.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=h["name"],
                    callback_data=HackathonPickCallback(
                        hackathon_id=h["id"]
                    ).pack(),
                )
            ]
            for h in hacks
        ]
    )

    await message.answer("Выберите хакатон:", reply_markup=keyboard)


@router.callback_query(HackathonPickCallback.filter())
async def pick_export_type(callback: CallbackQuery, callback_data: HackathonPickCallback):
    hid = callback_data.hackathon_id

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Участники",
                    callback_data=ExportKindCallback(hid, "participants").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Команды",
                    callback_data=ExportKindCallback(hid, "teams").pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text("Тип выгрузки:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(ExportKindCallback.filter())
async def send_export(callback: CallbackQuery, callback_data: ExportKindCallback, api):
    try:
        file_bytes = await api.download_hackathon_export(
            callback_data.hackathon_id,
            callback.from_user.id,
            callback_data.kind,
        )
    except BackendAPIError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    filename = f"hackathon_{callback_data.hackathon_id}_{callback_data.kind}.xlsx"

    await callback.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption="Готово",
    )

    await callback.answer()

    markup = await safe_menu(api, callback.from_user.id)
    await callback.message.answer("Меню:", reply_markup=markup)