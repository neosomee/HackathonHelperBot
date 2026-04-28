from aiogram.fsm.state import State, StatesGroup


class HackathonCreateState(StatesGroup):
    name = State()
    description = State()
    schedule_url = State()
    recruitment_open = State()
