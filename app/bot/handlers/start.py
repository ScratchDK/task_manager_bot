from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app.bot.dialogs.keyboards import get_return_keyboard
from app.bot.dispatcher import bot
from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal
from app.models import User
from app.models.task import TaskStatusEnum
from app.services.task_service import get_task_by_id, get_task_with_assignee
from app.services.user_service import get_or_create_user
import logging

logger = logging.getLogger(__name__)

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

        if not user.is_active:
            user.is_active = True
            await db.commit()
            await db.refresh(user)

        # Парсин payload (start=task_123)
        args = message.text.split()
        task_id = None
        if len(args) > 1:
            payload = args[1]
            if payload.startswith("task_"):
                try:
                    task_id = int(payload.split("_")[1])
                except ValueError:
                    pass

        if task_id:
            #task = await get_task_by_id(db, task_id)  Проблема MissingGreenlet
            task = await get_task_with_assignee(db, task_id)

            if not task:
                await message.answer("❌ Задача не найдена.")
            elif task.assignee_id != user.id:
                await message.answer("❌ Вы не являетесь исполнителем этой задачи.")
            elif task.status in [TaskStatusEnum.completed, TaskStatusEnum.cancelled]:
                await message.answer("❌ Эта задача уже выполнена или отменена.")
            else:
                # Сохраняем команду /start в состояние
                await MessageManager.add_message(state, message)

                # Пользователь активировался, показываем задачу
                task_text = (
                    f"✅ Вы назначены исполнителем задачи!\n\n"
                    f"📝 {task.title}\n"
                    f"📄 {task.description or 'Без описания'}\n"
                    f"🚨 Приоритет: {task.priority}\n"
                    f"📅 Срок: {task.due_date.strftime('%d.%m.%Y') if task.due_date else 'не установлен'}\n"
                    f"👤 Создатель: {task.created_by.username or task.created_by.telegram_chat_id}\n"
                    f"🆔 ID: {task.id}"
                )
                # Сохраняем сообщение с задачей
                sent_task = await message.answer(task_text)
                await MessageManager.add_message(state, sent_task)


                # Если задача была в статусе pending переводим в in_progress
                if task.status == TaskStatusEnum.pending:
                    task.status = TaskStatusEnum.in_progress
                    await db.commit()

                creator = await db.get(User, task.created_by_id)
                if creator:
                    try:
                        await bot.send_message(
                            chat_id=creator.telegram_chat_id,
                            text=(
                                f"✅ Исполнитель {user.username or user.first_name or str(user.telegram_chat_id)} принял задачу!\n\n"
                                f"📝 {task.title}\n"
                                f"🆔 ID: {task.id}\n\n"
                                f"Теперь можно отслеживать выполнение."
                            )
                        )
                    except Exception as e:
                        logger.error(f"Не удалось уведомить создателя {creator.id}: {e}")

                menu_btn = await message.answer(
                    "🏠 Нажмите кнопку ниже, чтобы перейти в главное меню",
                    reply_markup=get_return_keyboard()
                )
                await MessageManager.add_message(state, menu_btn)
                return

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
