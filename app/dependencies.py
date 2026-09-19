from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal

# --- Зависимость для БД ---
# Aiogram не использует Depends, в боте вариант через middleware
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД."""
    async with AsyncSessionLocal() as db:
        yield db
