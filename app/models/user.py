from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"  # Имя в БД

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")

    # Задачи, которые пользователь создал
    created_tasks = relationship("Task", foreign_keys="Task.created_by_id", back_populates="created_by")

    # Задачи, которые пользователю назначили
    assigned_tasks = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
