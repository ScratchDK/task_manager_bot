from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)

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
        [KeyboardButton(text="📅 Сегодня"), KeyboardButton(text="📅 Завтра")],
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
