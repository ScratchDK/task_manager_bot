from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.utils.message_manager import MessageManager
from app.bot.dialogs.keyboards import get_return_keyboard

router = Router()

main_menu_message = (
    "🏠 Главное меню:\n"
    "🤖 Доступные команды:\n\n"
    "/new_task - ➕ Создать задачу\n"
    "/my_tasks - 📋 Мои задачи\n"
    "/categories - 🏷️ Категории\n"
    "/help - ❓ Помощь"
)

help_text = (
    "🤖 Доступные команды:\n\n"
    "/start - 👋 Регистрация\n"
    "/new_task - ➕ Создать задачу\n"
    "/my_tasks - 📋 Мои задачи\n"
    "/categories - 🏷️ Мои категории\n"
    "/new_category - ➕ Создать категорию\n"
    "/edit_category (id) (имя) - ✏️ Редактировать категорию\n"
    "/delete_category (id) - 🗑️ Удалить категорию\n"
    "/help - ❓ Помощь"
)


# Обработчик инлайн-кнопки "В главное меню"
@router.callback_query(lambda c: c.data == "return_to_main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Универсальный обработчик возврата в главное меню."""
    await MessageManager.clear_all_and_state(callback.message, state)
    sent = await callback.message.answer(main_menu_message)
    await MessageManager.add_message(state, sent)
    await callback.answer()


# Обработчик Reply-кнопки "В главное меню"
@router.message(lambda msg: msg.text == "🏠 В главное меню")
async def return_to_main_menu_text(message: types.Message, state: FSMContext):
    """Обработчик для Reply-кнопки возврата."""
    await MessageManager.clear_all_and_state(message, state)
    sent = await message.answer(main_menu_message)
    await MessageManager.add_message(state, sent)


@router.message(Command("help"))
async def help_command(message: types.Message, state: FSMContext):
    """Показывает список команд."""
    await MessageManager.delete_before_new_dialog(message, state)
    await MessageManager.add_and_send(state, message, help_text, reply_markup=get_return_keyboard())


async def show_main_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню и сохраняет его ID."""
    sent = await message.answer(main_menu_message)
    if state:
        await MessageManager.add_message(state, sent)
