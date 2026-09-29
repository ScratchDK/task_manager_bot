from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import UserResponse
from app.dependencies import get_db
from app.services.user_service import get_user_by_chat_id_or_username

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/{telegram_chat_id}", response_model=UserResponse)
async def get_user(telegram_chat_id: str, db: AsyncSession = Depends(get_db),):
    """Получить информацию о пользователе по его telegram_chat_id."""
    user = await get_user_by_chat_id_or_username(db, chat_id=telegram_chat_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
