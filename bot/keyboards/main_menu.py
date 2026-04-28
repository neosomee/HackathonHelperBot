from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(*, is_organizer: bool = False, can_create_hackathon: bool = False):
    keyboard = [
        [
            KeyboardButton(text="👤 Мой профиль"),
            KeyboardButton(text="ℹ️ Помощь"),
        ],
        [KeyboardButton(text="📅 Сейчас в расписании")],
    ]
    if can_create_hackathon:
        keyboard.append([KeyboardButton(text="➕ Новый хакатон")])
    if is_organizer:
        keyboard.append([KeyboardButton(text="📊 Выгрузки организатора")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


async def main_menu_for_user(api, telegram_id: int):
    is_organizer = False
    can_create = False
    try:
        perm = await api.get_hackathon_permissions(telegram_id)
        is_organizer = bool(perm.get("is_organizer"))
        can_create = bool(perm.get("can_create_hackathon"))
    except Exception:
        try:
            data = await api.get_organized_hackathons(telegram_id)
            is_organizer = bool(data.get("hackathons"))
        except Exception:
            pass
    return main_menu(is_organizer=is_organizer, can_create_hackathon=can_create)
