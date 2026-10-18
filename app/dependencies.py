from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.models import User

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal

security = HTTPBearer()


# --- Зависимость для БД ---
# Aiogram не использует Depends, в боте вариант через middleware
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии БД."""
    async with AsyncSessionLocal() as db:
        yield db


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db),
) -> User:
    """Получает текущего пользователя по JWT-токену. Для проверки активности пользователя."""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Проверка активности
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is not active")

    return user
