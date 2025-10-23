from aiogram.fsm.state import State, StatesGroup


class PlantStates(StatesGroup):
    """Состояния для работы с растениями"""
    waiting_question = State()
    editing_plant_name = State()
    choosing_plant_to_grow = State()
    planting_setup = State()
    waiting_growing_photo = State()
    adding_diary_entry = State()
    waiting_state_update_photo = State()
