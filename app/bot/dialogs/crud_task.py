import asyncio
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           ReplyKeyboardRemove)

from app.bot.dialogs.keyboards import (get_confirm_keyboard,
                                       get_due_date_keyboard,
                                       get_priority_keyboard,
                                       get_return_keyboard)
from app.bot.dispatcher import bot
from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal
from app.services.category_service import get_user_cats
from app.services.task_service import (create_task, delete_task,
                                       get_task_by_id, get_user_tasks)
from app.services.user_service import get_user_by_chat_id_or_username

from .states import CreateTaskStates

router = Router()


# --- Обработчики кнопок ---
@router.callback_query(lambda c: c.data == "cancel_creation")
async def cancel_creation(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет создание задачи и возвращает в главное меню."""
    await callback.message.edit_text("❌ Создание задачи отменено.")  # TODO: Подредактировать
    await asyncio.sleep(1)
    await MessageManager.clear_all(callback.message, state)
    await state.clear()
    await callback.message.answer(
        "👋 Возвращаюсь в главное меню.\n"
        "Используйте команды:\n"
        "/new_task - ➕ Создать задачу\n"
        "/my_tasks - 📋 Мои задачи\n"
        "/categories - 🏷️ Категории"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("complete_task_"))
async def complete_task(callback: types.CallbackQuery):
    """Отмечает задачу как выполненную."""
    task_id = int(callback.data.split("_")[2])

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)
            return

        # Находим задачу
        task = await get_task_by_id(db, task_id)
        if not task:
            await callback.answer("❌ Задача не найдена.", show_alert=True)
            return

        # Проверяем, что пользователь — создатель или исполнитель
        if task.created_by_id != user.id and task.assignee_id != user.id:
            await callback.answer("❌ Нет прав.", show_alert=True)
            return

        # Меняем статус
        task.status = "completed"
        await db.commit()

        # Редактируем сообщение, убирая кнопки
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ Задача выполнена!",
            reply_markup=None
        )
        await callback.answer("✅ Задача выполнена!")


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


# --- Обработчики ---

@router.message(Command("new_task"))
async def start_create_task(message: types.Message, state: FSMContext):
    """Начинает процесс создания задачи."""
    await state.set_state(CreateTaskStates.waiting_for_title)  # Устанавливаем состояние, для понимания на каком этапе диалог
    await MessageManager.add_and_send(
        state,
        message,
        "📝 Введите заголовок задачи:",
        reply_markup=get_return_keyboard())  # Отправляем и сохраняем сообщение
    await MessageManager.add_message(state, message)  # Сохраняем сообщение пользователя


@router.message(CreateTaskStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    """Обрабатывает ввод заголовка."""
    await state.update_data(title=message.text)
    await state.set_state(CreateTaskStates.waiting_for_description)
    await MessageManager.add_and_send(
        state,
        message,
        "📄 Введите описание (можно пропустить, отправьте '-' )",
        reply_markup=get_return_keyboard())
    await MessageManager.add_message(state, message)


@router.message(CreateTaskStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    """Обрабатывает ввод описания."""
    description = None if message.text == "-" else message.text
    await state.update_data(description=description)
    await state.set_state(CreateTaskStates.waiting_for_due_date)
    await MessageManager.add_and_send(state, message,
        "📅 Укажите дату выполнения: 📅",
        reply_markup=get_due_date_keyboard()
    )
    await MessageManager.add_and_send(
        state, message, "Доступные варианты ниже 👇⌨️", reply_markup=get_return_keyboard()
    )
    await MessageManager.add_message(state, message)


@router.message(CreateTaskStates.waiting_for_due_date)
async def process_due_date(message: types.Message, state: FSMContext):
    """Обрабатывает выбор даты."""
    today = datetime.now().date()
    due_date_str = None  # Храним как строку!

    if message.text == "📅 Сегодня":
        due_date_str = today.isoformat()
    elif message.text == "📅 Завтра":
        due_date_str = (today + timedelta(days=1)).isoformat()
    elif message.text == "📅 Через 3 дня":
        due_date_str = (today + timedelta(days=3)).isoformat()
    elif message.text == "📅 Через неделю":
        due_date_str = (today + timedelta(days=7)).isoformat()
    elif message.text == "⬅️ Пропустить":
        due_date_str = None
    else:
        # Попытка распознать дату в свободном формате (простой вариант)
        try:
            parsed_date = datetime.strptime(message.text, "%d-%m-%Y").date()
            due_date_str = parsed_date.isoformat()
        except ValueError:
            await message.answer("⚠️ Неверный формат. Используйте ДД-ММ-ГГГГ или выберите из кнопок.")
            return

    await state.update_data(due_date=due_date_str)
    await state.set_state(CreateTaskStates.waiting_for_priority)
    await MessageManager.add_and_send(
        state,
        message,
        "🚨 Выберите приоритет: 🔴🟡🟢",
        reply_markup=get_priority_keyboard()
    )
    await MessageManager.add_and_send(
        state, message, "Доступные варианты ниже 👇⌨️", reply_markup=get_return_keyboard()
    )
    await MessageManager.add_message(state, message)


@router.message(CreateTaskStates.waiting_for_priority)
async def process_priority(message: types.Message, state: FSMContext):
    """Обрабатывает выбор приоритета."""
    priority_map = {
        "🔴 Высокий": "high",
        "🟡 Средний": "medium",
        "🟢 Низкий": "low",
    }
    priority = priority_map.get(message.text)
    if not priority and priority != "🏠 В главное меню":
        await MessageManager.add_and_send(state, message,"⚠️ Пожалуйста, используйте кнопки для выбора ниже 👇")
        await MessageManager.add_message(state, message)
        return

    await state.update_data(priority=priority)

    # Проверяем, есть ли категории у пользователя
    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        categories = await get_user_cats(db, user.id) if user else []

    if categories:
        await state.set_state(CreateTaskStates.waiting_for_category)
        # Простой вывод категорий (можно заменить на кнопки)
        cat_list = "\n".join([f"{cat.id} - {cat.name}" for cat in categories])
        await MessageManager.add_and_send(state, message,
            f"🏷️ Выберите категорию (введите ID) или отправьте '-' для пропуска:\n\n{cat_list}",
            reply_markup=ReplyKeyboardRemove()
        )
        await MessageManager.add_message(state, message)
    else:
        # Если категорий нет — сразу создаём задачу
        await ask_for_assignee(message, state)


@router.message(CreateTaskStates.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    """Обрабатывает выбор категории."""
    category_id = None
    if message.text != "-":
        try:
            category_id = int(message.text)
        except ValueError:
            await MessageManager.add_and_send(state, message,"⚠️ Введите корректный ID категории или '-' для пропуска.")
            await MessageManager.add_message(state, message)
            return

    await state.update_data(category_id=category_id)
    await ask_for_assignee(message, state)


async def ask_for_assignee(message: types.Message, state: FSMContext):
    """Спрашивает пользователя, кому назначить задачу."""
    await state.set_state(CreateTaskStates.waiting_for_assignee_input)
    await MessageManager.add_and_send(state, message,
        "👤 Введите username исполнителя (например, @ivan) или его ID (число).\n"
        "Если хотите оставить задачу за собой - отправьте '-'.",
        reply_markup=ReplyKeyboardRemove()
    )
    await MessageManager.add_message(state, message)


@router.message(CreateTaskStates.waiting_for_assignee_input)
async def process_assignee_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод исполнителя."""
    text = message.text.strip()

    if text == "-":
        # Пропуск — назначаем на себя
        await state.update_data(assignee_id=None)
        await finalize_task_creation(message, state)
        return

    # Ищем пользователя
    async with AsyncSessionLocal() as db:
        if text.isdigit():
            user = await get_user_by_chat_id_or_username(db, chat_id=text)
        else:
            user = await get_user_by_chat_id_or_username(db, username=text)

        if not user:
            await MessageManager.add_and_send(state, message,
                "⚠️ Пользователь не найден. Проверьте username или ID и попробуйте снова.\n"
                "Или отправьте '-' для назначения на себя."
            )
            await MessageManager.add_message(state, message)
            return

        # Сохраняем найденного пользователя в состояние
        await state.update_data(
            assignee_candidate_id=user.id,
            assignee_candidate_name=user.username or user.first_name or str(user.telegram_chat_id)
        )

        # Показываем подтверждение
        await state.set_state(CreateTaskStates.waiting_for_assignee_confirm)
        await MessageManager.add_and_send(state, message,
            f"👤 Найден пользователь: {user.username or user.first_name} (ID: {user.telegram_chat_id})\n"
            "Назначить его исполнителем?",
            reply_markup=get_confirm_keyboard(user.id)
        )
        await MessageManager.add_message(state, message)


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


# --- Функция финализации создания задачи ---
async def finalize_task_creation(message: types.Message, state: FSMContext):
    """Создает задачу и завершает диалог."""
    data = await state.get_data()

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            await state.clear()
            return

        # Преобразуем дату из date в datetime (если она есть)
        due_date = None
        due_date_str = data.get("due_date")
        if due_date_str:
            due_date = datetime.fromisoformat(due_date_str)

        task = await create_task(
            db=db,
            user=user,
            title=data["title"],
            description=data.get("description"),
            due_date=due_date,
            priority=data.get("priority", "medium"),
            category_id=data.get("category_id"),
            assignee_id=data.get("assignee_id"),
        )

    # Формируем ответ
    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "🟡")
    due_date_str = task.due_date.strftime("%d.%m.%Y") if task.due_date else "не установлена"

    assignee_display = "Вы (создатель)"

    if task.assignee_id and task.assignee_id != task.created_by_id:
        assignee_display = task.assignee.username or task.assignee.first_name or str(task.assignee.telegram_chat_id)

        try:
            await bot.send_message(
                chat_id=task.assignee.telegram_chat_id,
                text=(
                    f"📩 Вам назначена задача!\n\n"
                    f"📝 {task.title}\n"
                    f"📄 {task.description or 'Без описания'}\n"
                    f"🚨 Приоритет: {task.priority}\n"
                    f"📅 Срок: {task.due_date.strftime('%d.%m.%Y') if task.due_date else 'не установлен'}"
                )
            )
        except Exception as e:
            print(f"❌ Не удалось отправить уведомление исполнителю {task.assignee.telegram_chat_id}: {e}")

            await message.answer(
                f"ℹ️ Задача создана, но не удалось уведомить исполнителя.\n"
                f"Возможно, пользователь ещё не начал диалог с ботом.",
                reply_markup=ReplyKeyboardRemove()
            )
            # TODO: Важно!!! Данный шаг доработать в первую очередь

    await MessageManager.clear_all(message, state)

    await MessageManager.add_and_send(state, message,
        f"✅ Задача создана!\n\n"
        f"📝 {task.title}\n"
        f"📄 {task.description or 'Без описания'}\n"
        f"🚨 Приоритет: {priority_emoji} {task.priority}\n"
        f"📅 Срок: {due_date_str}\n"
        f"👤 Исполнитель: {assignee_display}\n"
        f"🆔 ID: {task.id}",
        reply_markup=get_return_keyboard()
    )
    await state.clear()


# --- Удаление задачи /delete_task ---
@router.message(Command("delete_task"))
async def delete_task_command(message: types.Message, state: FSMContext):
    """Удаляет задачу по ID."""
    # TODO: Потом доработать чтобы было более интуитивно
    await state.clear()
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ Использование: /delete_task <ID задачи>")
        return

    try:
        task_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, chat_id=str(message.chat.id))
        if not user:
            await message.answer("❌ Пользователь не найден.")
            return

        success = await delete_task(db, task_id, user)
        if success:
            await message.answer(f"✅ Задача #{task_id} удалена.")
        else:
            await message.answer(
                f"❌ Не удалось удалить задачу #{task_id}.\n"
                "Возможно, она не найдена или у вас нет прав."
            )


# --- Просмотр задач /my_tasks ---
@router.message(Command("my_tasks"))
async def list_tasks(message: types.Message, state: FSMContext):
    """Показывает последние задачи пользователя с кнопками."""
    await MessageManager.delete_before_new_dialog(message, state)

    await MessageManager.add_message(state, message)  # Сохраняем команду пользователя

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            sent = await message.answer("❌ Пользователь не найден. Используйте /start")
            await MessageManager.add_message(state, sent)
            return

        tasks = await get_user_tasks(db, user)

    if not tasks:
        sent = await message.answer("📭 У вас пока нет задач.\n\nИспользуйте /new_task для создания.")
        await MessageManager.add_message(state, sent)

        # Отправляем кнопку возврата
        menu_btn = await message.answer("🏠", reply_markup=get_return_keyboard())
        await MessageManager.add_message(state, menu_btn)
        return

    priority_display = {
        "high": "🔴 Высокий",
        "medium": "🟡 Средний",
        "low": "🟢 Низкий",
    }
    status_display = {
        "pending": "⏳ Ожидает",
        "in_progress": "🔄 В работе",
        "completed": "✅ Выполнена",
        "cancelled": "❌ Отменена",
    }

    for task in tasks:
        priority_value = task.priority.value if hasattr(task.priority, 'value') else task.priority
        status_value = task.status
        due_date_str = task.due_date.strftime("%d.%m.%Y") if task.due_date else "—"

        text = (
            f"📝 {task.title}\n"
            f"{priority_display.get(priority_value, '🟡 Средний')}\n"
            f"{status_display.get(status_value, '⏳ Ожидает')}\n"
            f"📅 Срок: {due_date_str}\n"
            f"📅 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        if task.description:
            short_desc = task.description[:50] + "..." if len(task.description) > 50 else task.description
            text += f"📄 {short_desc}\n"

        # Создаём кнопки
        buttons = []

        if task.status != "completed":
            buttons.append(
                InlineKeyboardButton(
                    text="✅ Выполнить",
                    callback_data=f"complete_task_{task.id}"
                )
            )

        if task.created_by_id == user.id:
            buttons.append(
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"delete_task_{task.id}"
                )
            )

        # Отправляем задачу и сохраняем её
        if buttons:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
            sent = await message.answer(text, reply_markup=keyboard)
        else:
            sent = await message.answer(text)

        # Сохраняем каждое сообщение с задачей
        await MessageManager.add_message(state, sent)

    # ✅ Отправляем кнопку возврата в главное меню
    menu_btn = await message.answer("🏠", reply_markup=get_return_keyboard())
    await MessageManager.add_message(state, menu_btn)
