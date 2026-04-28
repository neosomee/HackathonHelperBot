from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu(
    *,
    is_organizer: bool = False,
    can_create_hackathon: bool = False,
):
    """
    Главное меню Telegram-бота.

    Логика:
    - базовые кнопки всегда
    - доп. кнопки — по ролям
    """

    keyboard = [
        [
            KeyboardButton(text="👤 Мой профиль"),
            KeyboardButton(text="ℹ️ Помощь"),
        ],
        [
            KeyboardButton(text="📅 Сейчас в расписании"),
        ],
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
    """
    Динамическое меню под пользователя.

    Устойчивое к падению backend:
    - сначала permissions
    - fallback → организатор через список хакатонов
    - fallback → базовое меню
    """

    try:
        perm = await api.get_hackathon_permissions(telegram_id)

        return main_menu(
            is_organizer=bool(perm.get("is_organizer")),
            can_create_hackathon=bool(perm.get("can_create_hackathon")),
        )

    except Exception:
        # fallback 1 — проверка через хакатоны
        try:
            data = await api.get_organized_hackathons(telegram_id)

            return main_menu(
                is_organizer=bool(data.get("hackathons")),
                can_create_hackathon=False,
            )

        except Exception:
            # fallback 2 — дефолт
            return main_menu()