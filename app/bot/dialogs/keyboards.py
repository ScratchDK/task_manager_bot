from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)

from app.models import User


# Reply-кнопка = отправка текста в чат, message.text
# Inline-кнопка = callback-запрос боту

# --- Кнопки ---
def add_return_button():
    """Возвращает инлайн-кнопку возврата в главное меню."""
    return [InlineKeyboardButton(text="🏠 В главное меню", callback_data="return_to_main_menu")]

def add_return_reply_button():
    """Возвращает Reply-кнопку возврата в главное меню."""
    return [KeyboardButton(text="🏠 В главное меню")]


# --- Клавиатуры ---
# TODO: Пока не понятно почему не работает так как описано в инструкции, потом разобраться!
# def get_contact_keyboard():
#     """Клавиатура с кнопкой выбора контакта."""
#     button = KeyboardButton(text="👤 Выбрать из контактов", request_contact=True)
#     return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)


def get_return_keyboard():
    """Клавиатура с кнопкой возврата в меню."""
    return InlineKeyboardMarkup(inline_keyboard=[add_return_button()])


def get_priority_keyboard():
    """Клавиатура для выбора приоритета."""
    buttons = [
        [KeyboardButton(text="🔴 Высокий")],
        [KeyboardButton(text="🟡 Средний")],
        [KeyboardButton(text="🟢 Низкий")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_due_date_keyboard():
    """Клавиатура для быстрого выбора даты."""
    buttons = [
        [KeyboardButton(text="📅 Через час"), KeyboardButton(text="📅 Завтра")],
        [KeyboardButton(text="📅 Через 3 дня"), KeyboardButton(text="📅 Через неделю")],
        [KeyboardButton(text="⬅️ Пропустить")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_confirm_keyboard(user_id: int,):
    """Клавиатура для подтверждения назначения."""
    buttons = [
        [
            InlineKeyboardButton(text=f"✅ Да", callback_data=f"assign_confirm_{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="assign_cancel"),
        ],
        add_return_button()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Новые клавиатуры ---
def get_copy_or_menu_keyboard():
    """Клавиатура: сформировать сообщение или вернуться в меню."""
    buttons = [
        [InlineKeyboardButton(text="📝 Сформировать сообщение", callback_data="copy_message_start")],
        add_return_button()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_copy_actions_keyboard(user_id: int, task_id: int):
    """Клавиатура для шага копирования: скопировать, написать, в меню."""
    buttons = [
        [InlineKeyboardButton(text="📋 Скопировать текст", callback_data=f"copy_message_{task_id}")],
        [InlineKeyboardButton(text="👤 Написать исполнителю", url=f"tg://user?id={user_id}")],
        add_return_button()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_assignee_keyboard(users: list[User]) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с частыми исполнителями."""
    buttons = []
    for user in users[:3]:  # Берём только 3
        display_name = user.username or user.first_name or str(user.telegram_chat_id)
        buttons.append([
            InlineKeyboardButton(
                text=f"👤 {display_name}",
                callback_data=f"assignee_fast_{user.id}"
            )
        ])

    buttons.append(add_return_button())
    return InlineKeyboardMarkup(inline_keyboard=buttons)
