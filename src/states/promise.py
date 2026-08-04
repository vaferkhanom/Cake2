"""FSM States for Promise Bot."""

from aiogram.fsm.state import State, StatesGroup


class PromiseStates(StatesGroup):
    # Promise creation flow
    waiting_for_content = State()
    waiting_for_confirmation = State()
    waiting_for_deadline_choice = State()
    waiting_for_deadline_value = State()
    waiting_for_target = State()
    waiting_for_friend_id = State()