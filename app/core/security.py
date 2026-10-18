from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # bcrypt - медленный алгоритм (чтобы был не выгоден брутфорс)


# --- JWT ---
# JSON Web Token. Это строка, которая содержит:
# Payload (данные: sub = user_id, exp = expiration)
# Подпись (создана с SECRET_KEY)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создаёт access-токен (короткоживущий)."""
    to_encode = data.copy()   # Копия payload
    expire = datetime.now(timezone.utc) + (  # Время жизни токена
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})  # # добавляем время жизни и тип
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    """Создаёт refresh-токен (долгоживущий, 7 дней)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    """Проверяем подпись токена и возвращаем payload."""
    try:
        return jwt.decode(token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM],)
    except JWTError:
        return None


# --- Пароли ---

def hash_password(password: str) -> str:
    """Хеширует пароль."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Проверяет пароль."""
    return pwd_context.verify(plain_password, password_hash)
