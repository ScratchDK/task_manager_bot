from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"
    category_id: Optional[int] = None
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    """Схема для создания задачи."""
    pass


class TaskUpdate(BaseModel):
    """Схема для обновления задачи."""
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    category_id: Optional[int] = None
    assignee_id: Optional[int] = None


class TaskResponse(BaseModel):
    """Схема для ответа с задачей."""
    id: int
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    priority: str
    status: str
    category_id: Optional[int]
    assignee_id: Optional[int]
    created_by_id: int
    created_at: datetime
    completed_at: Optional[datetime]
    completion_comment: Optional[str]

    class Config:
        from_attributes = True  # Чтобы Pydantic мог работать с ORM-объектами


class UserResponse(BaseModel):
    """Схема для ответа с пользователем."""
    id: int
    telegram_chat_id: str
    username: Optional[str]
    first_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Auth ---

class TelegramLoginRequest(BaseModel):
    """Логин через Telegram (по chat_id)."""
    telegram_chat_id: str


class EmailRegisterRequest(BaseModel):
    """Регистрация через email + пароль."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    telegram_chat_id: Optional[str] = None


class EmailLoginRequest(BaseModel):
    """Логин через email + пароль."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Ответ с токенами."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Запрос на обновление токена."""
    refresh_token: str
