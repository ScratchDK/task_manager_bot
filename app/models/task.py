import enum
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class PriorityEnum(enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class TaskStatusEnum(enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    archived = "archived"
    review = "review"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)  # Срок выполнения
    priority = Column(SQLEnum(PriorityEnum), default=PriorityEnum.medium)
    status = Column(SQLEnum(TaskStatusEnum), default=TaskStatusEnum.pending)

    # Флаг, что задача отменена из-за не активности исполнителя
    cancelled_by_inactivity = Column(Boolean, default=False)

    # Связь с категорией (опционально)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Исполнитель задачи
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    category = relationship("Category", back_populates="tasks")

    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks")  # Создал задачу
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")  # Исполнитель

    # --- Поля связанные с проверкой выполнения задачи ---
    # Дата отправки на проверку (для отслеживания)
    review_requested_at = Column(DateTime, nullable=True)

    # Дата выполнения задачи
    completed_at = Column(DateTime, nullable=True)
