from aiogram.fsm.state import State, StatesGroup


class CreateTaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_due_date = State()
    waiting_for_priority = State()
    waiting_for_category = State()
    waiting_for_assignee_input = State()
    waiting_for_assignee_confirm = State()
    waiting_for_copy_message = State()  # Исполнитель не активен, копируем сообщение для оправки через владельца задачи


class CategoryStates(StatesGroup):
    waiting_for_name = State()  # Создание
    waiting_for_edit_id = State()  # Редактирование — запрос ID
    waiting_for_edit_name = State()  # Редактирование — запрос нового имени
    waiting_for_delete_id = State()  # Удаление — запрос ID
