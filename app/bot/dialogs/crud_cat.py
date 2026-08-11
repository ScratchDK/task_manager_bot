from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from app.bot.dialogs.keyboards import get_return_keyboard
from app.bot.dialogs.states import CategoryStates
from app.bot.utils.message_manager import MessageManager
from app.core.database import AsyncSessionLocal
from app.services.category_service import *
from app.services.user_service import get_user_by_chat_id_or_username

router = Router()


# --- Просмотр категорий /categories ---
@router.message(Command("categories"))
async def list_categories(message: types.Message, state: FSMContext):
    await MessageManager.delete_before_new_dialog(message, state)

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await MessageManager.add_and_send(state, message, "❌ Пользователь не найден. Используйте /start")
            return

        categories = await get_user_cats(db, user.id)

    if not categories:
        await MessageManager.add_and_send(state, message,
            "🏷️ У вас пока нет категорий.\n\n"
            "Используйте /new_category для создания.",
            reply_markup=get_return_keyboard()
        )
        return

    response = "🏷️ Ваши категории:\n\n"
    for cat in categories:
        response += f"📁 {cat.name} (ID: {cat.id})\n"
    response += "\n\nКоманды для управления:\n"
    response += "/new_category - ➕ Создать\n"
    response += "/edit_category - ✏️ Редактировать\n"
    response += "/delete_category - 🗑️ Удалить"

    await MessageManager.add_and_send(state, message, response, reply_markup=get_return_keyboard())


# --- Создание категории ---
@router.message(Command("new_category"))
async def start_create_category(message: types.Message, state: FSMContext):
    await MessageManager.delete_before_new_dialog(message, state)
    await state.set_state(CategoryStates.waiting_for_name)
    await MessageManager.add_and_send(state, message, "📝 Введите название новой категории:")


@router.message(CategoryStates.waiting_for_name)
async def process_category_name(message: types.Message, state: FSMContext):
    await MessageManager.add_message(state, message)

    name = message.text.strip()
    if not name:
        await MessageManager.add_and_send(state, message,"⚠️ Название не может быть пустым. Попробуйте снова:")
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await MessageManager.add_and_send(state, message,"❌ Используйте /start")
            return

        category = await create_cat(db, user, name)

    await MessageManager.add_and_send(
        state, message,
        f"✅ Категория '{category.name}' создана! (ID: {category.id})",
        reply_markup=get_return_keyboard()
    )


# --- Редактирование категории (диалог) ---
@router.message(Command("edit_category"))
async def start_edit_category(message: types.Message, state: FSMContext):
    await message.delete()
    await state.set_state(CategoryStates.waiting_for_edit_id)
    await MessageManager.add_and_send(state, message,
        "✏️ Введите ID категории, которую хотите отредактировать:\n\n"
            "Чтобы посмотреть ID, используйте /categories",
             reply_markup=get_return_keyboard()
    )


@router.message(CategoryStates.waiting_for_edit_id)
async def process_edit_id(message: types.Message, state: FSMContext):
    await MessageManager.add_message(state, message)
    try:
        category_id = int(message.text.strip())
    except ValueError:
        await MessageManager.add_and_send(state, message, "❌ ID должен быть числом. Попробуйте снова:")
        return

    # Проверяем, существует ли категория
    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await message.answer("❌ Используйте /start")
            await state.clear()
            return

        category = await get_cat_by_id(db, category_id, user.id)
        if not category:
            await MessageManager.add_and_send(state, message,
                f"❌ Категория с ID {category_id} не найдена или у вас нет прав.\n"
                "Попробуйте снова:"
            )
            return

        # Сохраняем ID в состояние
        await state.update_data(edit_category_id=category_id)

    await state.set_state(CategoryStates.waiting_for_edit_name)
    await MessageManager.add_and_send(state, message,
        f"📝 Введите новое название для категории '{category.name}':"
    )


@router.message(CategoryStates.waiting_for_edit_name)
async def process_edit_name(message: types.Message, state: FSMContext):
    await MessageManager.add_message(state, message)

    new_name = message.text.strip()
    if not new_name:
        await MessageManager.add_and_send(state, message,"⚠️ Название не может быть пустым. Попробуйте снова:")
        return

    data = await state.get_data()
    category_id = data.get("edit_category_id")

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await MessageManager.add_and_send(state, message,"❌ Используйте /start")
            return

        category = await get_cat_by_id(db, category_id, user.id)
        if not category:
            await MessageManager.add_and_send(state, message,f"❌ Категория с ID {category_id} не найдена.")
            return

        updated = await update_cat(db, category, new_name)

    await MessageManager.add_and_send(state, message,
        f"✅ Категория обновлена:\n"
        f"📁 {updated.name} (ID: {updated.id})",
         reply_markup=get_return_keyboard()
    )


# --- Удаление категории (диалог) ---
@router.message(Command("delete_category"))
async def start_delete_category(message: types.Message, state: FSMContext):
    await message.delete()
    await state.set_state(CategoryStates.waiting_for_delete_id)
    await MessageManager.add_and_send(state, message,
        "ID категорий 👆\n"
        "🗑️ Введите ID категории, которую хотите удалить:",
        reply_markup=get_return_keyboard()
    )


@router.message(CategoryStates.waiting_for_delete_id)
async def process_delete_id(message: types.Message, state: FSMContext):
    await MessageManager.add_message(state, message)
    try:
        category_id = int(message.text.strip())
    except ValueError:
        await MessageManager.add_and_send(state, message,"❌ ID должен быть числом. Попробуйте снова:")
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_chat_id_or_username(db, str(message.chat.id))
        if not user:
            await MessageManager.add_and_send(state, message,"❌ Используйте /start")
            return

        category = await get_cat_by_id(db, category_id, user.id)
        if not category:
            await MessageManager.add_and_send(state, message,
                f"❌ Категория с ID {category_id} не найдена или у вас нет прав.\n"
                "Попробуйте снова:"
            )
            return

        await delete_cat(db, category)
    await MessageManager.add_and_send(state, message,
              f"🗑️ Категория с ID {category_id} удалена.",
              reply_markup=get_return_keyboard()
            )
