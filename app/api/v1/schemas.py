from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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