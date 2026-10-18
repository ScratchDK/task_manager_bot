async def test_register(test_client):
    response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "test12345"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login(test_client, test_user_with_email):
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_protected_endpoint_without_token(test_client):
    response = await test_client.get("/api/v1/tasks/my")
    assert response.status_code == 403


async def test_protected_endpoint_with_token(test_client, test_user_with_email):
    login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "test12345"},
    )
    token = login.json()["access_token"]

    response = await test_client.get(
        "/api/v1/tasks/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200