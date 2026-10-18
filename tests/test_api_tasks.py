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


async def test_get_my_tasks(test_user_with_email, test_client):
    """GET /api/v1/tasks/my возвращает задачи."""
    # Логин
    login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    token = login.json()["access_token"]

    # Запрос
    response = await test_client.get(
        "/api/v1/tasks/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_create_task(test_user_with_email, test_client):
    """POST /api/v1/tasks/ создаёт задачу."""
    login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    token = login.json()["access_token"]

    response = await test_client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "New Task", "priority": "high"},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "New Task"


async def test_update_task(test_user_with_email, test_client, db_session):
    """PATCH /api/v1/tasks/{id} обновляет задачу."""
    from app.services.task_service import create_task

    # Создаём задачу
    task = await create_task(db=db_session, user=test_user_with_email, title="Old Title")

    # Логин > токен
    login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    token = login.json()["access_token"]

    # Запрос с токеном
    response = await test_client.patch(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "New Title", "priority": "low"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


async def test_delete_task(test_user_with_email, test_client, db_session):
    """DELETE /api/v1/tasks/{id} удаляет задачу."""
    from app.services.task_service import create_task

    # Создаём задачу
    task = await create_task(db=db_session, user=test_user_with_email, title="To Delete")

    # Логин > токен
    login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    token = login.json()["access_token"]

    # Запрос с токеном
    response = await test_client.delete(
        f"/api/v1/tasks/{task.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204
