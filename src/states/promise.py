from aiogram.fsm.state import State, StatesGroup

class PromiseForm(StatesGroup):
    waiting_for_content = State()
    waiting_for_initial_confirm = State()
    waiting_for_target = State()
    waiting_for_receiver_id = State()
