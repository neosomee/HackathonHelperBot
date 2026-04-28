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

from bot.keyboards.main_menu import main_menu_for_user
from bot.services.api import BackendAPIError
from bot.states.hackathon_create import HackathonCreateState

router = Router()


def _cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def _yes_no_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Набор открыт"), KeyboardButton(text="⛔ Набор закрыт")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


class HackathonPickCallback(CallbackData, prefix="org_h"):
    hackathon_id: int


class ExportKindCallback(CallbackData, prefix="org_x"):
    hackathon_id: int
    kind: str


@router.message(F.text == "➕ Новый хакатон")
async def hackathon_create_entry(message: Message, state: FSMContext, api):
    try:
        perm = await api.get_hackathon_permissions(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Не удалось проверить права: {exc.message}")
        return

    if not perm.get("can_create_hackathon"):
        await message.answer(
            "Создание хакатонов сейчас недоступно.\n\n"
            "Как получить доступ:\n"
            "• Укажите ваш числовой Telegram ID в переменной ORGANIZER_BOOTSTRAP_TELEGRAM_IDS "
            "в файле .env на машине с Django и перезапустите сервер.\n"
            "• Или зарегистрируйтесь в боте, затем в Django Admin откройте Hackathon → организаторы "
            "и добавьте свой User; после этого вы сможете создавать новые хакатоны через API/Mini App/бот."
        )
        return

    await state.set_state(HackathonCreateState.name)
    await message.answer("Введите название хакатона:", reply_markup=_cancel_kb())


@router.message(StateFilter(HackathonCreateState.name), F.text)
async def hackathon_create_name(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        markup = await main_menu_for_user(api, message.from_user.id)
        await message.answer("Отменено.", reply_markup=markup)
        return

    if not text:
        await message.answer("Название не может быть пустым. Введите ещё раз:")
        return

    await state.update_data(name=text)
    await state.set_state(HackathonCreateState.description)
    await message.answer(
        "Краткое описание (или отправьте «-» чтобы пропустить):",
        reply_markup=_cancel_kb(),
    )


@router.message(StateFilter(HackathonCreateState.description), F.text)
async def hackathon_create_description(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        markup = await main_menu_for_user(api, message.from_user.id)
        await message.answer("Отменено.", reply_markup=markup)
        return

    desc = "" if text == "-" else text
    await state.update_data(description=desc)
    await state.set_state(HackathonCreateState.schedule_url)
    await message.answer(
        "Ссылка на Google Таблицу с расписанием (или «-» чтобы пропустить):",
        reply_markup=_cancel_kb(),
    )


@router.message(StateFilter(HackathonCreateState.schedule_url), F.text)
async def hackathon_create_schedule(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        markup = await main_menu_for_user(api, message.from_user.id)
        await message.answer("Отменено.", reply_markup=markup)
        return

    url = "" if text == "-" else text
    await state.update_data(schedule_sheet_url=url)
    await state.set_state(HackathonCreateState.recruitment_open)
    await message.answer(
        "Капитаны могут подключать команды к этому хакатону?",
        reply_markup=_yes_no_kb(),
    )


@router.message(StateFilter(HackathonCreateState.recruitment_open), F.text)
async def hackathon_create_recruitment(message: Message, state: FSMContext, api):
    text = (message.text or "").strip()
    if text == "❌ Отмена":
        await state.clear()
        markup = await main_menu_for_user(api, message.from_user.id)
        await message.answer("Отменено.", reply_markup=markup)
        return

    if "открыт" in text.lower() and "закрыт" not in text.lower():
        is_open = True
    elif "закрыт" in text.lower() or "close" in text.lower():
        is_open = False
    else:
        await message.answer("Нажмите «✅ Набор открыт» или «⛔ Набор закрыт».")
        return

    data = await state.get_data()
    await state.clear()

    tid = message.from_user.id
    try:
        result = await api.create_hackathon(
            telegram_id=tid,
            name=data["name"],
            description=data.get("description", ""),
            schedule_sheet_url=data.get("schedule_sheet_url", ""),
            is_team_join_open=is_open,
        )
    except BackendAPIError as exc:
        markup = await main_menu_for_user(api, tid)
        await message.answer(f"Не удалось создать: {exc.message}", reply_markup=markup)
        return

    h = result.get("hackathon") or {}
    markup = await main_menu_for_user(api, tid)
    await message.answer(
        f"Хакатон создан: {h.get('name', '')}\n"
        f"slug: {h.get('slug', '')}\n"
        f"id: {h.get('id', '')}",
        reply_markup=markup,
    )


@router.message(F.text == "📊 Выгрузки организатора")
async def organizer_entry(message: Message, api):
    try:
        data = await api.get_organized_hackathons(message.from_user.id)
    except BackendAPIError as exc:
        await message.answer(f"Не удалось загрузить хакатоны: {exc.message}")
        return

    hacks = data.get("hackathons") or []
    if not hacks:
        await message.answer(
            "У вас нет прав организатора на существующих хакатонах.\n"
            "Создайте хакатон через «➕ Новый хакатон» (если доступно) "
            "или попросите администратора добавить вас в организаторы в Django Admin."
        )
        return

    rows = [
        [
            InlineKeyboardButton(
                text=h["name"],
                callback_data=HackathonPickCallback(hackathon_id=h["id"]).pack(),
            )
        ]
        for h in hacks
    ]
    await message.answer("Выберите хакатон:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(HackathonPickCallback.filter())
async def organizer_pick_kind(callback: CallbackQuery, callback_data: HackathonPickCallback):
    hid = callback_data.hackathon_id
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Участники (.xlsx)",
                    callback_data=ExportKindCallback(hackathon_id=hid, kind="participants").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Команды (.xlsx)",
                    callback_data=ExportKindCallback(hackathon_id=hid, kind="teams").pack(),
                )
            ],
        ]
    )
    await callback.message.edit_text("Тип выгрузки:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(ExportKindCallback.filter())
async def organizer_send_export(callback: CallbackQuery, callback_data: ExportKindCallback, api):
    telegram_id = callback.from_user.id
    try:
        body = await api.download_hackathon_export(
            callback_data.hackathon_id,
            telegram_id,
            callback_data.kind,
        )
    except BackendAPIError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    suffix = "participants" if callback_data.kind == "participants" else "teams"
    filename = f"hackathon_{callback_data.hackathon_id}_{suffix}.xlsx"
    await callback.message.answer_document(
        BufferedInputFile(body, filename=filename),
        caption="Готово.",
    )
    await callback.answer()
    markup = await main_menu_for_user(api, telegram_id)
    await callback.message.answer("Меню:", reply_markup=markup)
