from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.dialogs.crud_task import show_tasks_page
from app.bot.utils.message_manager import MessageManager
from app.services.user_service import get_user_by_chat_id_or_username

router = Router()


@router.callback_query(lambda c: c.data.startswith("tasks_page_"))
async def paginate_tasks(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession):
    """Обрабатывает переход между страницами задач."""
    page = int(callback.data.split("_")[2])

    user = await get_user_by_chat_id_or_username(db, callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Удаляем старое сообщение с задачами
    await MessageManager.clear_messages(callback.message, state)

    # Показываем новую страницу
    await show_tasks_page(callback.message, state, db, user, page=page)
    await callback.answer()
