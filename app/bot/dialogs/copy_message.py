from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.dispatcher import bot
from app.services.task_service import get_task_with_assignee
from app.bot.dialogs.states import CreateTaskStates
from app.bot.dialogs.keyboards import get_copy_actions_keyboard

router = Router()


# --- Обработчики формирования и копирования текста для отправки исполнителю ---
@router.callback_query(CreateTaskStates.waiting_for_copy_message, lambda c: c.data == "copy_message_start")
async def start_copy_message(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
    """Показывает готовое сообщение для копирования."""
    data = await state.get_data()
    task_id = data.get("task_id")

    task = await get_task_with_assignee(db, task_id)

    if not task:
        await callback.answer("❌ Задача не найдена.", show_alert=True)
        return

    assignee = task.assignee

    # Редактируем предыдущее сообщение, показываем текст
    await callback.message.edit_text(
        f"Выберете вариант ниже для продолжения👇",
        reply_markup=get_copy_actions_keyboard(assignee.telegram_chat_id, task.id)
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("copy_message_"))
async def copy_message_handler(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
    """Копирует сообщение в буфер обмена."""
    task_id = int(callback.data.split("_")[-1])

    task = await get_task_with_assignee(db, task_id)
    if not task:
        await callback.answer("❌ Задача не найдена.", show_alert=True)
        return

    bot_username = (await bot.me()).username
    copy_text = (
        f"👋 Привет! Пользователь {task.created_by.username} назначил тебе задачу.\n\n"
        f"📝 Название: {task.title}\n"
        f"📄 Описание: {task.description or 'Без описания'}\n"
        f"🚨 Приоритет: {task.priority}\n"
        f"📅 Срок: {task.due_date.strftime('%d.%m.%Y') if task.due_date else 'не установлен'}\n\n"
        f"Запусти бота, чтобы принять задачу: https://t.me/{bot_username}?start=task_{task.id}\n"
        f"Либо проигнорируй данное сообщение."
    )

    # Короткое уведомление
    await callback.answer("📋 Текст скопирован!", show_alert=True, cache_time=60)

    # Полный текст в чат
    await callback.message.answer(f"📋 Скопируйте текст ниже:\n\n```\n{copy_text}\n```", parse_mode="Markdown")
