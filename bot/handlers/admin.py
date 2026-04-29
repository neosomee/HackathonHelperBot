from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config.admins import ADMIN_IDS
from bot.services.api import BackendAPIError

router = Router()

PAGE_SIZE = 8  # 4 ряда по 2 кнопки


class AdminUsersPageCallback(CallbackData, prefix="adm_users"):
    page: int


class AdminPickUserCallback(CallbackData, prefix="adm_pick"):
    telegram_id: int
    page: int


class AdminSetRoleCallback(CallbackData, prefix="adm_role"):
    telegram_id: int
    role: str
    page: int


def _chunked(items, size: int = 2):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _users_markup(users: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    buttons = []
    for user in users:
        name = (user.get("full_name") or "Без имени").strip()
        label = name if len(name) <= 24 else f"{name[:21]}…"
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminPickUserCallback(
                    telegram_id=int(user["telegram_id"]),
                    page=page,
                ).pack(),
            )
        )

    for row in _chunked(buttons, 2):
        rows.append(row)

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminUsersPageCallback(page=page - 1).pack(),
            )
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="➡️ Далее",
                callback_data=AdminUsersPageCallback(page=page + 1).pack(),
            )
        )
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def _roles_markup(target_telegram_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Админ",
                    callback_data=AdminSetRoleCallback(
                        telegram_id=target_telegram_id,
                        role="ADMIN",
                        page=page,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Капитан+Организатор",
                    callback_data=AdminSetRoleCallback(
                        telegram_id=target_telegram_id,
                        role="CAPTAIN_ORGANIZER",
                        page=page,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Организатор",
                    callback_data=AdminSetRoleCallback(
                        telegram_id=target_telegram_id,
                        role="ORGANIZER",
                        page=page,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data=AdminUsersPageCallback(page=page).pack(),
                )
            ],
        ]
    )


async def _safe_edit(message: Message, text: str, reply_markup=None):
    try:
        if message.text != text or message.reply_markup != reply_markup:
            await message.edit_text(text, reply_markup=reply_markup)
    except Exception as exc:
        if "message is not modified" not in str(exc):
            raise exc


async def _render_users_page(message: Message, api, admin_telegram_id: int, page: int, *, edit: bool = False):
    data = await api.admin_list_users(admin_telegram_id=admin_telegram_id, page=page, page_size=PAGE_SIZE)
    users = data.get("users") or []
    total_pages = int(data.get("total_pages") or 1)
    current_page = int(data.get("page") or page)

    if not users:
        text = "Пользователи не найдены."
        if edit:
            await _safe_edit(message, text, reply_markup=None)
        else:
            await message.answer(text)
        return

    text = f"Пользователи · страница {current_page}/{total_pages}\n\nВыберите человека:"
    markup = _users_markup(users, current_page, total_pages)

    if edit:
        await _safe_edit(message, text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("admin"))
async def admin_entry(message: Message, api):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа.")
        return

    try:
        await _render_users_page(message, api, message.from_user.id, page=1, edit=False)
    except BackendAPIError as exc:
        await message.answer(f"Ошибка: {exc.message}")


@router.callback_query(AdminUsersPageCallback.filter())
async def admin_users_page(callback: CallbackQuery, callback_data: AdminUsersPageCallback, api):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        await _render_users_page(callback.message, api, callback.from_user.id, page=callback_data.page, edit=True)
    except BackendAPIError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    await callback.answer()


@router.callback_query(AdminPickUserCallback.filter())
async def admin_pick_user(callback: CallbackQuery, callback_data: AdminPickUserCallback, api):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        data = await api.admin_list_users(
            admin_telegram_id=callback.from_user.id,
            page=callback_data.page,
            page_size=PAGE_SIZE,
        )
    except BackendAPIError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    users = data.get("users") or []
    user = next((u for u in users if int(u["telegram_id"]) == int(callback_data.telegram_id)), None)

    title = (user.get("full_name") if user else f"Telegram ID: {callback_data.telegram_id}") if isinstance(user, dict) else f"Telegram ID: {callback_data.telegram_id}"

    text = f"Пользователь: {title}\n\nВыберите роль:"
    markup = _roles_markup(callback_data.telegram_id, callback_data.page)

    await _safe_edit(callback.message, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(AdminSetRoleCallback.filter())
async def admin_set_role(callback: CallbackQuery, callback_data: AdminSetRoleCallback, api):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        result = await api.admin_set_user_role(
            admin_telegram_id=callback.from_user.id,
            target_telegram_id=callback_data.telegram_id,
            role=callback_data.role,
        )
    except BackendAPIError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    user = result.get("user", {})
    full_name = user.get("full_name", str(callback_data.telegram_id))

    await callback.answer("Роль обновлена")
    await _render_users_page(callback.message, api, callback.from_user.id, page=callback_data.page, edit=True)