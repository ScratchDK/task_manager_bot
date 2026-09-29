from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.dependencies import get_db
from app.models.task import Task, TaskStatusEnum
from app.services.task_service import (
    create_task,
    delete_task,
    get_task_by_id,
    get_user_tasks,
)
from app.services.user_service import get_user_by_chat_id_or_username

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("/user/{telegram_chat_id}", response_model=List[TaskResponse])
async def list_user_tasks(telegram_chat_id: str, db: AsyncSession = Depends(get_db),):
    """Получить все задачи пользователя/"""
    user = await get_user_by_chat_id_or_username(db, chat_id=telegram_chat_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tasks = await get_user_tasks(db, user)
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db),):
    """Получить задачу по ID."""
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(task_data: TaskCreate, telegram_chat_id: str, db: AsyncSession = Depends(get_db),):
    """
    Создать новую задачу.
    Query parameter `telegram_chat_id` — кто создаёт задачу.
    """
    user = await get_user_by_chat_id_or_username(db, chat_id=telegram_chat_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task = await create_task(
        db=db,
        user=user,
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority,
        category_id=task_data.category_id,
        assignee_id=task_data.assignee_id,
    )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_data: TaskUpdate, db: AsyncSession = Depends(get_db),):
    """
    Обновить задачу.
    Можно менять: title, description, due_date, priority, status, category_id, assignee_id.
    """
    task = await get_task_by_id(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Обновляем только переданные поля
    update_data = task_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "priority" and value:
            task.priority = value
        elif field == "status" and value:
            task.status = TaskStatusEnum(value)
        else:
            setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_api(task_id: int, telegram_chat_id: str, db: AsyncSession = Depends(get_db),):
    """
    Удалить задачу.
    Только создатель может удалить задачу.
    """
    user = await get_user_by_chat_id_or_username(db, chat_id=telegram_chat_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    success = await delete_task(db, task_id, user)
    if not success:
        raise HTTPException(status_code=403, detail="Cannot delete task")

    return None
