from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def role_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👑 Капитан")],
            [KeyboardButton(text="👤 Участник")],
        ],
        resize_keyboard=True,
    )