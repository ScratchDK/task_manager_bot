"""
Middleware для aiogram, который создаёт сессию БД для каждого апдейта.

Что делает:
1. Перехватывает входящий апдейт (сообщение, callback)
2. Создаёт новую сессию БД
3. Прокидывает её в хендлер через data["db"]
4. Закрывает сессию после обработки
"""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal


class DbSessionMiddleware(BaseMiddleware):
    """
    Создаёт AsyncSession для каждого апдейта и прокидывает в хендлер.

    В хендлере сессия доступна как аргумент `db`:
        async def handler(message: Message, db: AsyncSession):
            ...
    """

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        # Создаём сессию
        async with AsyncSessionLocal() as session:  # Обертка ДО
            data["db"] = session  # Добавляем сессию в data - оттуда aiogram подставит её в хендлер
            # Вызываем обработчик
            return await handler(event, data)  # Вызов следующего
