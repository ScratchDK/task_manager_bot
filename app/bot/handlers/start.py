from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.dispatcher import bot
from app.services.user_service import get_or_create_user
from app.core.database import AsyncSessionLocal

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
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
    await message.answer(
        f"👋 Привет, {message.from_user.first_name or 'друг'}!\n\n"
        f"✅ Ты успешно зарегистрирован!\n"
        f"🆔 Твой ID: {user.telegram_chat_id}\n\n"
        "Используй команды:\n"
        "/new_task - ➕ Создать задачу\n"
        "/my_tasks - 📋 Мои задачи\n"
        "/categories - 🏷️ Категории"
    )
