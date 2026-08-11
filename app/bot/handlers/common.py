from aiogram import Router, types
from aiogram.fsm.context import FSMContext

from app.bot.menu import main_menu_message
from app.bot.utils.message_manager import MessageManager

# TODO: Возможно отказаться от всего common.py?

router = Router()


@router.callback_query(lambda c: c.data == "return_to_main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Универсальный обработчик возврата в главное меню."""
    # Удаляем все сообщения из state (включая возможное старое меню)
    await MessageManager.clear_all(callback.message, state)
    await state.clear()

    # Отправляем новое меню
    sent = await callback.message.answer(main_menu_message)

    # Сохраняем ID нового меню в state
    await MessageManager.add_message(state, sent)

    await callback.answer()


@router.message(lambda msg: msg.text == "🏠 В главное меню")
async def return_to_main_menu_text(message: types.Message, state: FSMContext):
    """Обработчик для Reply-кнопки возврата."""
    # Удаляем все сообщения из state
    await MessageManager.clear_all(message, state)
    await state.clear()

    # Отправляем новое меню
    sent = await message.answer(main_menu_message)

    # Сохраняем ID нового меню в state
    await MessageManager.add_message(state, sent)
