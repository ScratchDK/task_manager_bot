from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.api.v1.schemas import EmailLoginRequest, EmailRegisterRequest, RefreshRequest, TokenResponse #TelegramLoginRequest

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.dependencies import get_db
from app.models import User
from app.services.user_service import get_user_by_chat_id_or_username

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_tokens(user: User) -> TokenResponse:
    """Создаёт access + refresh токены для пользователя."""
    token_data = {"sub": str(user.id), "chat_id": user.telegram_chat_id}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# TODO: Возможно для будущей логики
# --- Telegram ---
#
# @router.post("/telegram/login", response_model=TokenResponse)
# async def telegram_login(
#         data: TelegramLoginRequest,
#         db: AsyncSession = Depends(get_db),
# ):
#     """Логин через telegram_chat_id (для бота)."""
#     user = await get_user_by_chat_id_or_username(db, chat_id=data.telegram_chat_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     if not user.is_active:
#         raise HTTPException(status_code=403, detail="User is not active")
#
#     return _build_tokens(user)


# --- Email ---

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: EmailRegisterRequest, db: AsyncSession = Depends(get_db),):
    """Регистрация через email + пароль."""
    # Проверка: email уже существует?
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Создаём или находим пользователя
    if data.telegram_chat_id:
        # Привязка к существующему Telegram-пользователю
        user = await get_user_by_chat_id_or_username(db, chat_id=data.telegram_chat_id)
        if not user:
            user = User(
                telegram_chat_id=data.telegram_chat_id,
                is_active=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
    else:
        # Создаём пользователя без Telegram
        temp_chat_id = f"email_{uuid.uuid4().hex[:16]}"
        user = User(
            telegram_chat_id=temp_chat_id,
            is_active=True,  #TODO: Пока активен, но после того как сделаю подтверждения email, поменять!!!
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Привязываем email + пароль к пользователю
    user.email = data.email
    user.password_hash = hash_password(data.password)
    await db.commit()
    await db.refresh(user)

    return _build_tokens(user)


@router.post("/login", response_model=TokenResponse)
async def email_login(
        data: EmailLoginRequest,
        db: AsyncSession = Depends(get_db),
):
    """Логин через email + пароль."""
    query = select(User).where(User.email == data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _build_tokens(user)


# --- Общее ---

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Обновление access-токена через refresh-токен."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user = await db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return _build_tokens(user)
