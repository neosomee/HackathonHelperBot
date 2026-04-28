from aiogram.fsm.state import State, StatesGroup


class HackathonCreateState(StatesGroup):
    """
    FSM для пошагового создания хакатона.

    Поток:
    1. name
    2. description
    3. schedule_sheet_url
    4. recruitment_open
    """

    name = State()
    description = State()
    schedule_sheet_url = State()
    recruitment_open = State()