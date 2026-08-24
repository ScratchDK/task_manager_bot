import asyncio

from aiogram.fsm.context import FSMContext
from aiogram.types import Message


class MessageManager:
    """Управляет сообщениями в диалоге: сохраняет ID и удаляет все."""

    @staticmethod
    async def add_message(state: FSMContext, message: Message):
        """Добавляет ID сообщения (пользователя или бота) в состояние."""
        data = await state.get_data()
        messages = data.get("messages", [])  # Пытаемся взять список по ключу "messages". Если нет, создаем пустой.
        messages.append(message.message_id)
        await state.update_data(messages=messages)

    @staticmethod
    async def add_and_send(state: FSMContext, target: Message, text: str, **kwargs):
    # target - объект от которого мы отталкиваемся что бы отправить сообщение в тот же чат
        """
        Отправляет сообщение и автоматически сохраняет его ID.
        Возвращает отправленное сообщение.
        """
        sent = await target.answer(text, **kwargs)
        await MessageManager.add_message(state, sent)
        return sent

    @staticmethod
    async def clear_all_and_state(target: Message, state: FSMContext):
        """Удаляет все сообщения, сохранённые в состоянии, и очищает список."""
        data = await state.get_data()
        messages = data.get("messages", [])

        for msg_id in messages:
            try:
                await target.bot.delete_message(
                    chat_id=target.chat.id,
                    message_id=msg_id
                )
            except Exception:
                pass  # Сообщение уже удалено или нет прав

        # Очищаем список
        await state.update_data(messages=[])
        await state.clear()

    # TODO: !!!ДОРАБОТАТЬ👇!!!
    @staticmethod
    async def send_and_delete(target: Message, text: str, delay: int = 2, **kwargs):
        """
        Отправляет сообщение и удаляет его через указанное время.
        Сообщение НЕ сохраняется в состоянии (для временных уведомлений по типу: возвращаюсь в меню).
        """
        sent = await target.answer(text, **kwargs)

        # Запускаем таймер на удаление
        asyncio.create_task(MessageManager._delete_after_delay(sent, delay))
        return sent

    @staticmethod
    async def _delete_after_delay(message: Message, delay: int):
        """Внутренний метод для удаления сообщения после задержки."""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception:
            pass  # Сообщение уже удалено или нет прав

    @staticmethod
    async def delete_before_new_dialog(message: Message, state: FSMContext):
        await message.delete()  # Удаляем команду например /categories
        await MessageManager.clear_all_and_state(message, state)  # Удаляем все старые сообщения из чата
        await state.clear()  # Очищаем состояние
