from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.bot.dispatcher import bot
from app.bot.menu import show_main_menu
from app.bot.utils.message_manager import MessageManager
from app.models import User
from app.models.task import TaskStatusEnum
from app.services.task_service import get_task_by_id
from app.bot.dialogs.states import CommentStates
from app.bot.dialogs.keyboards import get_confirm_task_keyboard

router = Router()


@router.message(CommentStates.waiting_for_comment)
async def process_processing_comment(message: types.Message, state: FSMContext, db: AsyncSession,):
    """Принимает комментарий и отправляет задачу на доработку, либо добавляет комментарий при выполнении задачи исполнителем."""
    comment = message.text.strip()

    # Получаем ID задачи из состояния
    data = await state.get_data()
    task_id = data.get("task_id")
    comment_type = data.get("type_comment")

    task = await get_task_by_id(db, task_id)
    if not task:
        await message.answer("❌ Задача не найдена.")
        await show_main_menu(message, state)
        return

    if comment_type == "rework":
        if not comment:
            await message.answer("❌ Комментарий не может быть пустым. Напишите причину доработки:")
            return

        # Отправляем на доработку
        task.status = TaskStatusEnum.in_progress
        task.review_requested_at = None
        task.completion_comment = None
        await db.commit()

        # Уведомляем исполнителя
        assignee = await db.get(User, task.assignee_id)
        if assignee:
            await bot.send_message(
                chat_id=assignee.telegram_chat_id,
                text=(
                    f"🔄 Задача '{task.title}' отправлена на доработку.\n\n"
                    f"📝 Комментарий от создателя:\n{comment}\n\n"
                    f"Исправьте замечания и отправьте снова."
                )
            )

        # Очищаем состояние и показываем меню
        await MessageManager.send_and_delete(message, "✅ Задача отправлена на доработку с комментарием.", delay=3)
        await show_main_menu(message, state)

    elif comment_type == "completion":
        if not comment:
            await message.answer("❌ Комментарий не может быть пустым. Укажите доказательство выполнения задачи:")
            return

        # Исполнитель выполнил задачу, отправляем на проверку
        task.status = TaskStatusEnum.review
        task.review_requested_at = datetime.now()
        task.completion_comment = comment  # Комментарий исполнителя при выполнении задачи
        await db.commit()

        # Уведомляем создателя с кнопками
        creator = await db.get(User, task.created_by_id)
        if creator:
            await bot.send_message(
                chat_id=creator.telegram_chat_id,
                text=(
                    f"📩 Исполнитель {message.from_user.username or message.from_user.first_name or 'пользователь'} отправил задачу на проверку:\n\n"
                    f"📝 {task.title}\n"
                    f"📄 {task.description or 'Без описания'}\n\n"
                    f"💬 Комментарий: {comment}\n\n"
                    f"Примите решение:"
                ),
                reply_markup=get_confirm_task_keyboard(task.id)
            )

        await MessageManager.send_and_delete(message, "📤 Задача отправлена на проверку!", delay=3)
