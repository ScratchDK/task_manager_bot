from aiogram import Router, types
from aiogram.filters import Command
from app.services.category_service import get_user_categories
from app.services.user_service import get_user_by_chat_id_or_username
from app.core.database import AsyncSessionLocal

router = Router()

@router.message(Command("categories"))
async def list_categories(message: types.Message):
    """Показать список категорий."""
    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return

        categories = await get_user_categories(db, user.id)

    if not categories:
        await message.answer(
            "🏷️ У вас пока нет категорий.\n\n"
            "💡 Категории можно создать через API (в разработке)."
        )
        return

    response = "🏷️ Ваши категории:\n\n"
    for cat in categories:
        response += f"📁 {cat.name} (ID: {cat.id})\n"
    await message.answer(response)
