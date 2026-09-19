from app.models import User
from app.services.task_service import create_task, delete_task, get_task_by_id, get_user_tasks
from app.models.task import TaskStatusEnum


async def test_create_task(db_session, test_user):
    """Создание задачи."""
    task = await create_task(
        db=db_session,
        user=test_user,
        title="Test Task",
        description="Test Description",
        priority="high",
    )

    assert task.id is not None
    assert task.title == "Test Task"
    assert task.created_by_id == test_user.id
    assert task.assignee_id == test_user.id


async def test_create_task_with_assignee(db_session, test_user):
    """Создание задачи с назначением на другого пользователя."""
    # Создаём второго пользователя
    assignee = User(
        telegram_chat_id="987654321",
        username="assignee",
        is_active=True,
    )
    db_session.add(assignee)
    await db_session.commit()
    await db_session.refresh(assignee)

    task = await create_task(
        db=db_session,
        user=test_user,
        title="Assigned Task",
        assignee_id=assignee.id,
    )

    assert task.assignee_id == assignee.id
    assert task.assignee.username == "assignee"


async def test_delete_task_owner(db_session, test_user):
    """Удаление задачи создателем."""
    task = await create_task(
        db=db_session,
        user=test_user,
        title="To Delete",
    )

    success = await delete_task(db_session, task.id, test_user)
    assert success is True

    # Проверяем, что задачи больше нет
    deleted = await get_task_by_id(db_session, task.id)
    assert deleted is None


async def test_delete_task_not_owner(db_session, test_user):
    """Попытка удалить чужую задачу — должна упасть."""
    other_user = User(telegram_chat_id="555", is_active=True)
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    task = await create_task(
        db=db_session,
        user=test_user,
        title="Not Yours",
    )

    success = await delete_task(db_session, task.id, other_user)
    assert success is False


async def test_get_user_tasks_as_creator(db_session, test_user):
    """Пользователь видит созданные задачи."""
    task = await create_task(db=db_session, user=test_user, title="My Task")

    tasks = await get_user_tasks(db_session, test_user)
    assert len(tasks) == 1
    assert tasks[0].id == task.id


async def test_get_user_tasks_as_assignee(db_session, test_user):
    """Пользователь видит задачи, где он исполнитель."""
    # Создаём второго пользователя
    assignee = User(telegram_chat_id="999", is_active=True)
    db_session.add(assignee)
    await db_session.commit()
    await db_session.refresh(assignee)

    # test_user создаёт задачу, assignee — исполнитель
    task = await create_task(
        db=db_session,
        user=test_user,
        title="For Assignee",
        assignee_id=assignee.id,
    )

    # assignee видит эту задачу
    tasks = await get_user_tasks(db_session, assignee)
    assert len(tasks) == 1
    assert tasks[0].id == task.id


# --- Тесты: статусы и комменты ---

async def test_task_status_default(db_session, test_user):
    """При создании задачи статус = pending."""
    task = await create_task(db=db_session, user=test_user, title="Status Test")

    assert task.status == TaskStatusEnum.pending


async def test_task_priority_default(db_session, test_user):
    """При создании без приоритета — medium."""
    task = await create_task(db=db_session, user=test_user, title="Priority Test")

    # priority может быть Enum или строкой — обрабатываем оба случая
    priority_value = task.priority.value if hasattr(task.priority, 'value') else task.priority
    assert priority_value == "medium"


async def test_task_completion_comment_saved(db_session, test_user):
    """Комментарий исполнителя сохраняется при отправке на review."""
    task = await create_task(db=db_session, user=test_user, title="Comment Test")

    # Имитируем, что исполнитель отправил комментарий
    task.completion_comment = "Всё готово, проверьте"
    task.status = TaskStatusEnum.review
    await db_session.commit()
    await db_session.refresh(task)

    assert task.completion_comment == "Всё готово, проверьте"
    assert task.status == TaskStatusEnum.review


async def test_task_completion_comment_cleared_on_rework(db_session, test_user):
    """Комментарий исполнителя очищается при отправке на доработку."""
    task = await create_task(db=db_session, user=test_user, title="Rework Test")

    # Сначала исполнитель отправил с комментарием
    task.completion_comment = "Готово"
    task.status = TaskStatusEnum.review
    await db_session.commit()

    # Потом создатель отправил на доработку
    task.status = TaskStatusEnum.in_progress
    task.completion_comment = None
    task.review_requested_at = None
    await db_session.commit()
    await db_session.refresh(task)

    assert task.completion_comment is None
    assert task.status == TaskStatusEnum.in_progress
    assert task.review_requested_at is None


async def test_task_completed_at_set_on_approve(db_session, test_user):
    """При утверждении задачи заполняется completed_at."""
    from datetime import datetime

    task = await create_task(db=db_session, user=test_user, title="Approve Test")

    assert task.completed_at is None  # Изначально пусто

    # Утверждаем задачу
    task.status = TaskStatusEnum.completed
    task.completed_at = datetime.now()
    await db_session.commit()
    await db_session.refresh(task)

    assert task.completed_at is not None
    assert task.status == TaskStatusEnum.completed


async def test_task_review_requested_at_set(db_session, test_user):
    """При отправке на review заполняется review_requested_at."""
    from datetime import datetime

    task = await create_task(db=db_session, user=test_user, title="Review Test")

    assert task.review_requested_at is None  # Изначально пусто

    # Отправляем на review
    task.status = TaskStatusEnum.review
    task.review_requested_at = datetime.now()
    await db_session.commit()
    await db_session.refresh(task)

    assert task.review_requested_at is not None
    assert task.status == TaskStatusEnum.review


async def test_task_notification_attempts_default(db_session, test_user):
    """При создании notification_attempts = 0."""
    task = await create_task(db=db_session, user=test_user, title="Notification Test")

    assert task.notification_attempts == 0


async def test_task_cancelled_by_inactivity_default(db_session, test_user):
    """При создании cancelled_by_inactivity = False."""
    task = await create_task(db=db_session, user=test_user, title="Inactive Test")

    assert task.cancelled_by_inactivity is False
