from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession  # Тип для аннотации

from app.models.user import User


async def get_or_create_user(db: AsyncSession, tg_data: dict) -> User:  # tg_data из handlers/start
    """Найти или создать пользователя по данным из Telegram."""
    chat_id = str(tg_data["chat_id"])

    # Ищем пользователя
    query = select(User).where(User.telegram_chat_id == chat_id)  # Ленивый запрос
    result = await db.execute(query)  # Только тут обращаемся к БД
    user = result.scalar_one_or_none()  # Извлекаем единственный объект User или None из результата

    if user:
        return user

    # Создаем нового
    user = User(
        telegram_chat_id=chat_id,
        username=tg_data.get("username"),
        first_name=tg_data.get("first_name"),
        last_name=tg_data.get("last_name"),
    )
    db.add(user)  # Аналог save() из django, но INSERT еще не произошел
    await db.commit()  # Для атомарности, чтобы вся транзакция прошла (INSERT в БД (генерируется id))
    await db.refresh(user)  # refresh нужен для получения авто генерируемых полей, alchemy в отличие от django не делает автоматом (Загружаем свежие данные)
    return user


async def get_user_by_chat_id_or_username(db: AsyncSession, chat_id: str | int | None = None, username: str | None = None
                                          ) -> User | None:
    """Находит пользователя по telegram_chat_id или username."""

    if not chat_id and not username:
        return None

    conditions = []
    if chat_id:
        # Преобразуем chat_id в строку, если это int, (была ошибка несоответствия типов данных)
        chat_id_str = str(chat_id)
        conditions.append(User.telegram_chat_id == chat_id_str)
    if username:
        # Убираем @ если есть
        clean_username = username.lstrip('@')
        conditions.append(User.username == clean_username)

    query = select(User).where(or_(*conditions))  # Используем OR для поиска по любому из условий
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def is_user_active(db: AsyncSession, user_id: int) -> bool:
    """Проверяет, активен ли пользователь (запускал ли бота)."""
    user = await db.get(User, user_id)
    return user is not None and user.is_active
