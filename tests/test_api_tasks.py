from app.services.task_service import create_task


async def test_get_user(test_user, test_client):
    """GET /api/v1/tasks/user/{id} возвращает задачи."""
    response = await test_client.get(f"/api/v1/users/{test_user.telegram_chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_chat_id"] == test_user.telegram_chat_id


async def test_get_user_not_found(test_client):
    """GET /api/v1/users/{id} для несуществующего — 404."""
    response = await test_client.get("/api/v1/users/999999999")
    assert response.status_code == 404


async def test_get_tasks(test_user, test_client, db_session):
    """GET /api/v1/tasks/user/{id} возвращает задачи."""
    # Создаём задачу
    await create_task(db=db_session, user=test_user, title="API Task")

    response = await test_client.get(f"/api/v1/tasks/user/{test_user.telegram_chat_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "API Task"


async def test_create_task(test_user, test_client):
    """POST /api/v1/tasks/ создаёт задачу."""
    response = await test_client.post(
        "/api/v1/tasks/",
        params={"telegram_chat_id": test_user.telegram_chat_id},
        json={
            "title": "New Task",
            "description": "From API",
            "priority": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Task"
    assert data["priority"] == "high"


async def test_update_task(test_user, test_client, db_session):
    """PATCH /api/v1/tasks/{id} обновляет задачу."""
    from app.services.task_service import create_task
    task = await create_task(db=db_session, user=test_user, title="Old Title")

    response = await test_client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"title": "New Title", "priority": "low"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


async def test_delete_task(test_user, test_client, db_session):
    """DELETE /api/v1/tasks/{id} удаляет задачу."""
    from app.services.task_service import create_task
    task = await create_task(db=db_session, user=test_user, title="To Delete")

    response = await test_client.delete(
        f"/api/v1/tasks/{task.id}",
        params={"telegram_chat_id": test_user.telegram_chat_id},
    )
    assert response.status_code == 204
