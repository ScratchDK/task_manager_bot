from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.utils.message_manager import MessageManager

router = Router()


# --- Основное меню (Rich Message) ---
async def show_main_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню с Rich Message и сохраняет его ID."""

    # Формируем текст с HTML-разметкой
    main_menu_text = (
        "<b>🏠 Главное меню</b>\n"
        "<i>🤖 Доступные команды:</i>\n\n"
        "<code>/new_task</code> - ➕ Создать задачу\n"
        "<code>/my_tasks</code> - 📋 Мои задачи\n"
        "<code>/categories</code> - 🏷️ Категории\n"
        "<code>/help</code> - ❓ Помощь"
    )

    # Создаём инлайн-кнопки для быстрого доступа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать задачу", callback_data="new_task")],
        [InlineKeyboardButton(text="📋 Мои задачи", callback_data="my_tasks")],
        [InlineKeyboardButton(text="🏷️ Категории", callback_data="categories")]
    ])

    # Отправляем Rich Message
    sent = await message.answer(
        main_menu_text,
        parse_mode="HTML",  # Включаем HTML-форматирование
        reply_markup=keyboard
    )

    # Сохраняем ID меню в state (если есть состояние)
    if state:
        await MessageManager.add_message(state, sent)


# --- Обработчик для кнопок меню ---
@router.callback_query(lambda c: c.data in ["new_task", "my_tasks", "categories"])
async def menu_buttons_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие на кнопки меню."""
    await callback.answer()

    if callback.data == "new_task":
        # Здесь запускаешь создание задачи
        await callback.message.answer("📝 Запускаю создание задачи...")
        # Или вызываешь start_create_task
    elif callback.data == "my_tasks":
        # Здесь запускаешь список задач
        await callback.message.answer("📋 Показываю задачи...")
    elif callback.data == "categories":
        # Здесь запускаешь список категорий
        await callback.message.answer("🏷️ Показываю категории...")


# --- Обычное меню для старта (без Rich Message) ---
main_menu_message = (
    "🏠 Главное меню:\n"
    "🤖 Доступные команды:\n\n"
    "/new_task - ➕ Создать задачу\n"
    "/my_tasks - 📋 Мои задачи\n"
    "/categories - 🏷️ Категории\n"
    "/help - ❓ Помощь"
)


@router.message(Command("help"))
async def help_command(message: types.Message, state: FSMContext):
    """Показывает список команд."""
    await state.clear()
    # Отправляем обычное сообщение (без Rich Message)
    await message.answer(main_menu_message, parse_mode="HTML")
