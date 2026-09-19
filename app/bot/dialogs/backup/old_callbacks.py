import asyncio
from datetime import datetime

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.bot.dispatcher import bot
from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal
from app.models import User
from app.models.task import TaskStatusEnum
from app.services.task_service import get_task_by_id, delete_task
from app.services.user_service import get_user_by_chat_id_or_username
from app.bot.dialogs.states import CreateTaskStates
from app.bot.dialogs.crud_task import finalize_task_creation
from app.bot.dialogs.keyboards import get_copy_actions_keyboard, get_confirm_keyboard, get_confirm_task_keyboard

router = Router()


# --- Обработчики кнопок ---
@router.callback_query(lambda c: c.data == "cancel_creation")
async def cancel_creation(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет создание задачи и возвращает в главное меню."""
    await callback.message.edit_text("❌ Создание задачи отменено.")  # TODO: Подредактировать
    await asyncio.sleep(1)
    await MessageManager.clear_all_and_state(callback.message, state)
    await callback.message.answer(
        "👋 Возвращаюсь в главное меню.\n"
        "Используйте команды:\n"
        "/new_task - ➕ Создать задачу\n"
        "/my_tasks - 📋 Мои задачи\n"
        "/categories - 🏷️ Категории"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("complete_task_"))
async def complete_task(callback: types.CallbackQuery, state: FSMContext):
    """Отмечает задачу как выполненную."""
    task_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return

        # Находим задачу
        task = await get_task_by_id(db, task_id)

        # Проверяем, что задача не на проверке и не выполнена
        if task.status in [TaskStatusEnum.review, TaskStatusEnum.completed]:
            await callback.answer("❌ Задача уже на проверке или выполнена.", show_alert=True)
            return

        if not task:
            await callback.answer("❌ Задача не найдена.", show_alert=True)
            return

        # Проверяем, что пользователь — создатель или исполнитель
        if task.created_by_id != user.id and task.assignee_id != user.id:
            await callback.answer("❌ Нет прав.", show_alert=True)
            return

        # --- Логика проверки выполнения задачи ---
        if task.created_by_id == user.id:
            # Создатель выполнил свою задачу, сразу завершаем
            task.status = TaskStatusEnum.completed
            task.completed_at = datetime.now()
            await db.commit()
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ Задача выполнена!",
                reply_markup=None
            )
            await callback.answer("✅ Задача выполнена!")

        elif task.assignee_id == user.id:
            # Создатель выполнил задачу, отправляем на проверку
            task.status = TaskStatusEnum.review
            task.review_requested_at = datetime.now()
            await db.commit()
            await callback.message.edit_text(
                callback.message.text + "\n\n📤 Задача отправлена на проверку.",
                reply_markup=None
            )

        # Уведомляем создателя с кнопками
        creator = await db.get(User, task.created_by_id)
        if creator:
            await bot.send_message(
                chat_id=creator.telegram_chat_id,
                text=(
                    f"📩 Исполнитель {user.username} отправил задачу на проверку:\n\n"
                    f"📝 {task.title}\n"
                    f"📄 {task.description or 'Без описания'}\n\n"
                    f"Примите решение:"
                ),
                reply_markup=get_confirm_task_keyboard(task.id)
            )

        await callback.answer("📤 Задача отправлена на проверку!")
        return


# --- Новая логика подтверждения выполнения задач ---
@router.callback_query(lambda c: c.data.startswith("approve_task_"))
async def approve_task(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        task = await get_task_by_id(db, task_id)
        if not task:
            await callback.answer("❌ Задача не найдена.", show_alert=True)
            return

        # Проверка, что нажал создатель
        if task.created_by_id != callback.from_user.id:
            await callback.answer("❌ Нет прав.", show_alert=True)
            return

        # Утверждаем задачу
        task.status = TaskStatusEnum.completed
        task.completed_at = datetime.now()
        await db.commit()

        # Уведомляем исполнителя
        assignee = await db.get(User, task.assignee_id)
        if assignee:
            await bot.send_message(
                chat_id=assignee.telegram_chat_id,
                text=f"✅ Задача '{task.title}' утверждена и закрыта!"
            )

        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Задача утверждена и закрыта.",
            reply_markup=None
        )
        await callback.answer("✅ Задача утверждена!")


@router.callback_query(lambda c: c.data.startswith("rework_task_"))
async def rework_task(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        task = await get_task_by_id(db, task_id)
        if not task:
            await callback.answer("❌ Задача не найдена.", show_alert=True)
            return

        # Проверка, что нажал создатель
        if task.created_by_id != callback.from_user.id:
            await callback.answer("❌ Нет прав.", show_alert=True)
            return

        # Отправляем на доработку
        task.status = TaskStatusEnum.in_progress
        task.review_requested_at = None
        await db.commit()

        # Уведомляем исполнителя
        assignee = await db.get(User, task.assignee_id)
        if assignee:
            await bot.send_message(
                chat_id=assignee.telegram_chat_id,
                text=f"🔄 Задача '{task.title}' отправлена на доработку. Исправьте замечания и отправьте снова."
            )

        await callback.message.edit_text(
            callback.message.text + "\n\n🔄 Задача отправлена на доработку.",
            reply_markup=None
        )
        await callback.answer("🔄 Задача отправлена на доработку!")


@router.callback_query(lambda c: c.data.startswith("delete_task_"))
async def delete_task_callback(callback: types.CallbackQuery):
    """Удаляет задачу."""
    task_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return

        # Удаляем задачу
        success = await delete_task(db, task_id, user)

        if success:
            await callback.message.edit_text(
                callback.message.text + "\n\n🗑️ Задача удалена.",
                reply_markup=None
            )
            await callback.answer("🗑️ Задача удалена!")
        else:
            await callback.answer("❌ Не удалось удалить задачу.", show_alert=True)


@router.callback_query(CreateTaskStates.waiting_for_assignee_confirm)
async def process_assignee_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает подтверждение или отмену назначения."""
    if callback.data == "assign_cancel":
        await callback.message.edit_text("❌ Назначение отменено.")
        await callback.message.answer("Введите другого исполнителя или '-' для пропуска.")
        await state.set_state(CreateTaskStates.waiting_for_assignee_input)
        await callback.answer()
        return

    if callback.data.startswith("assign_confirm_"):
        assignee_id = int(callback.data.split("_")[2])
        data = await state.get_data()

        if data.get("assignee_candidate_id") == assignee_id:
            await state.update_data(assignee_id=assignee_id)
            await callback.message.edit_text("✅ Исполнитель назначен!")
            await finalize_task_creation(callback.message, state)
        else:
            await callback.message.edit_text("⚠️ Ошибка: выбранный пользователь не совпадает. Попробуйте снова.")
            await state.set_state(CreateTaskStates.waiting_for_assignee_input)

        await callback.answer()
        return


# --- Новые обработчики ---
@router.callback_query(lambda c: c.data.startswith("assignee_fast_"))
async def assignee_fast_selected(callback: types.CallbackQuery, state: FSMContext):
    """Выбор частого исполнителя."""
    user_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, chat_id=user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return

        await state.update_data(
            assignee_candidate_id=user.id,
            assignee_candidate_name=user.username or user.first_name or str(user.telegram_chat_id)
        )

    await state.set_state(CreateTaskStates.waiting_for_assignee_confirm)
    await callback.message.edit_text(
        f"👤 Найден пользователь: {user.username or user.first_name} (ID: {user.telegram_chat_id})\n"
        "Назначить его исполнителем?",
        reply_markup=get_confirm_keyboard(user.id)
    )
    await callback.answer()


# --- Обработчики формирования и копирования текста для отправки исполнителю ---
@router.callback_query(CreateTaskStates.waiting_for_copy_message, lambda c: c.data == "copy_message_start")
async def start_copy_message(callback: types.CallbackQuery, state: FSMContext):
    """Показывает готовое сообщение для копирования."""
    data = await state.get_data()
    task_id = data.get("task_id")

    async with AsyncSessionLocal() as db:
        task = await get_task_by_id(db, task_id)
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
async def copy_message_handler(callback: types.CallbackQuery, state: FSMContext):
    """Копирует сообщение в буфер обмена."""
    task_id = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as db:
        task = await get_task_by_id(db, task_id)
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
            f"Запусти бота, чтобы принять задачу: https://t.me/{bot_username}?start=task_{task.id}"
            f"Либо проигнорируй данное сообщение."
        )

        await callback.answer(
            f"📋 Текст скопирован!\n\n{copy_text}",
            show_alert=True,  # Показывает текст во всплывающем окне
            cache_time=60
        )
