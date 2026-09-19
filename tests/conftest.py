import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models import User, Task, Category


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",  # БД в оперативной памяти
        echo=False,                          # Не выводим SQL в консоль
    )

    # Создаём все таблицы на основе моделей
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine  # Отдаём движок тесту

    # После теста, закрываем движок
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Не сбрасываем объекты после commit
    )

    async with async_session() as session:
        yield session  # Отдаём сессию тесту
        # После теста сессия закроется автоматически


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        telegram_chat_id="123456789",
        username="test_user",
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user
