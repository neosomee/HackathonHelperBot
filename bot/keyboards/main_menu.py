from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu():
    """
    Главное меню Telegram-бота.

    ВАЖНО:
    - Mini App НЕ здесь (используется Menu Button)
    - Здесь только быстрые действия
    """

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Мой профиль"),
                KeyboardButton(text="ℹ️ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )