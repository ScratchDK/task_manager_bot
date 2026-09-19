from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.bot.dispatcher import bot
from app.bot.menu import show_main_menu
from app.bot.utils.message_manager import MessageManager
from app.models import User
from app.models.task import TaskStatusEnum
from app.services.task_service import get_task_by_id, delete_task
from app.services.user_service import get_user_by_chat_id_or_username
from app.bot.dialogs.states import CreateTaskStates, CommentStates
from app.bot.dialogs.crud_task import finalize_task_creation
from app.bot.dialogs.keyboards import get_confirm_keyboard

router = Router()


# --- Обработчики кнопок ---
@router.callback_query(lambda c: c.data == "cancel_creation")
async def cancel_creation(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет создание задачи и возвращает в главное меню."""
    await MessageManager.clear_all_and_state(callback.message, state)
    await MessageManager.send_and_delete(
        callback.message,
        "❌ Создание задачи отменено. Возвращаюсь в меню...",
        delay=2
    )
    # Показываем меню новым сообщением
    await show_main_menu(callback.message, state)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("complete_task_"))
async def complete_task(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
    # TODO: Для себя! middleware в main.py перед роутами, в middleware мы и создаем ключ db и передаем сессию
    """Отмечает задачу как выполненную."""
    task_id = int(callback.data.split("_")[2])

    user = await get_user_by_chat_id_or_username(db, callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден.", show_alert=True)
        return

    # Находим задачу
    task = await get_task_by_id(db, task_id)

    if not task:
        await callback.answer("❌ Задача не найдена.", show_alert=True)
        return

    # Проверяем, что задача не на проверке и не выполнена
    if task.status in [TaskStatusEnum.review, TaskStatusEnum.completed]:
        await callback.answer("❌ Задача уже на проверке или выполнена.", show_alert=True)
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
        # Редактируем изначальное сообщение кнопки выполнить в списке задач
        await callback.message.edit_text(callback.message.text + "\n\n✅ Задача выполнена!", reply_markup=None)
        # TODO: Проверить 👇
        await callback.answer("✅ Задача выполнена!")

    elif task.assignee_id == user.id:
        # Переключаем состояние
        await state.update_data(task_id=task_id, type_comment="completion")
        await state.set_state(CommentStates.waiting_for_comment)

        # Редактируем сообщение, чтобы убрать кнопки
        await callback.message.edit_text("В качестве подтверждения выполнения задачи укажите:\n"
                                         "текстовый комментарий, либо прикрепите файл.\n", reply_markup=None)
        await callback.answer()


# --- Новая логика подтверждения выполнения задач ---
@router.callback_query(lambda c: c.data.startswith("approve_task_"))
async def approve_task(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
    task_id = int(callback.data.split("_")[2])

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

    await MessageManager.send_and_delete(
        callback.message,
        "✅ Задача утверждена и закрыта!",
        delay=3
    )
    await show_main_menu(callback.message, state)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rework_task_"))
async def rework_task(callback: types.CallbackQuery, state: FSMContext):
    """Запрашивает комментарий для доработки."""
    task_id = int(callback.data.split("_")[2])

    # Сохраняем ID задачи в состояние и тип ожидаемого комментария
    await state.update_data(task_id=task_id, type_comment="rework")

    # Переключаем состояние
    await state.set_state(CommentStates.waiting_for_comment)

    # Редактируем сообщение, чтобы убрать кнопки
    await callback.message.edit_text(callback.message.text + "\n\n📝 Напишите причину доработки:", reply_markup=None)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("delete_task_"))
async def delete_task_callback(callback: types.CallbackQuery, db: AsyncSession,):
    """Удаляет задачу."""
    task_id = int(callback.data.split("_")[2])

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
async def process_assignee_confirm(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
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
            await finalize_task_creation(callback.message, state, db)
        else:
            await callback.message.edit_text("⚠️ Ошибка: выбранный пользователь не совпадает. Попробуйте снова.")
            await state.set_state(CreateTaskStates.waiting_for_assignee_input)

        await callback.answer()
        return


# --- Новые обработчики ---
@router.callback_query(lambda c: c.data.startswith("assignee_fast_"))
async def assignee_fast_selected(callback: types.CallbackQuery, state: FSMContext, db: AsyncSession,):
    """Выбор частого исполнителя."""
    user_id = int(callback.data.split("_")[2])

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
