from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.models.user import User

from sqlalchemy import func, desc


async def get_frequent_assignees(db: AsyncSession, user_id: int, limit: int = 3) -> list[User]:
    """Возвращает список пользователей, которых данный пользователь чаще всего назначал исполнителями."""
    # Подзапрос: считаем количество назначений для каждого assignee
    subquery = (
        select(
            Task.assignee_id,
            func.count(Task.id).label("count")  # Виртуальное поле с результатом
        )
        .where(
            Task.created_by_id == user_id,
            Task.assignee_id != user_id  # Исключаем самого себя
        )
        .group_by(Task.assignee_id)
        .subquery()  # Чтобы была возможность использовать в JOIN или FROM другого запроса
    )

    # Основной запрос: получаем пользователей с сортировкой по частоте
    query = (
        select(User)
        .join(subquery, User.id == subquery.c.assignee_id)
        .order_by(desc(subquery.c.count))  # .c. "columns" выбрать определенную колонку
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def create_task(db: AsyncSession, user: User, title: str, description: str = None,
    due_date: datetime = None, priority: str = "medium", category_id: int = None, assignee_id: int = None,) -> Task:
    """Создает новую задачу."""
    task = Task(
        title=title,
        description=description,
        due_date=due_date,
        priority=priority,
        category_id=category_id,
        created_by_id=user.id,
        assignee_id=assignee_id or user.id,  # Если не указан, исполнитель - создатель
    )
    db.add(task)
    await db.commit()

    # Для моментов когда нужен исполнитель
    if assignee_id and assignee_id != user.id:
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.assignee))  # selectinload - жадно подгружаем связанные данные
            .where(Task.id == task.id)
        )
        task = result.scalar_one()
    else:
        await db.refresh(task)

    return task


async def delete_task(db: AsyncSession, task_id: int, current_user: User) -> bool:
    """Удаляет задачу, если текущий пользователь имеет на это право."""
    # Находим задачу
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        return False

    # Проверяем права (только создатель может удалять)
    if task.created_by_id != current_user.id:
        return False

    await db.delete(task)
    await db.commit()
    return True


async def get_user_tasks(db: AsyncSession, user: User, limit: int = 10):
    """Получает последние задачи пользователя."""
    query = (
        select(Task)
        .where(Task.created_by_id == user.id)
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_task_by_id(db: AsyncSession, task_id: int) -> Task | None:
    """Получает задачу по ID."""
    query = select(Task).where(Task.id == task_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()
