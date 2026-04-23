from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    full_name = State()
    email = State()
    skills = State()
