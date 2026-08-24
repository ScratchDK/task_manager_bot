from app.services.user_service import get_user_by_chat_id_or_username
from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal


async def get_user_or_ask_start(message, state):
    """Проверяет пользователя. Возвращает User или None."""
    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await MessageManager.add_and_send(state, message, "❌ Пользователь не найден. Используйте /start")
            return None
        return user
