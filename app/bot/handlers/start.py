from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal
from app.services.user_service import get_or_create_user

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    # Сбрасываем состояние, если оно было
    await message.delete()  # Удаляем команду /start
    await MessageManager.clear_all_and_state(message, state)  # Удаляем все старые сообщения из чата
    await state.clear()  # Очищаем состояние

    # Получаем данные пользователя из Telegram
    tg_data = {
        "chat_id": message.chat.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name,
    }

    # Создаем сессию БД
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, tg_data)

    # Приветственное сообщение
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name or 'друг'}!\n\n"
        f"✅ Ты успешно зарегистрирован!\n"
        f"🆔 Твой ID: {user.telegram_chat_id}\n\n"
    )
    start_menu = (
        "Используй команды:\n"
        "/new_task - ➕ Создать задачу\n"
        "/my_tasks - 📋 Мои задачи\n"
        "/categories - 🏷️ Категории\n"
        "/help - ❓ Помощь"
    )

    await MessageManager.add_message(state, message)  # Сохраняем /start для удаления в дальнейшем.

    # Отдельно, чтобы при очистке чата было хоть одно сообщение, чтобы не выкидывало из чата каждый раз
    await message.answer(welcome_text)
    await MessageManager.add_and_send(state, message, start_menu)
