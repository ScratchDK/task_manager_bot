from app.services.user_service import get_or_create_user, get_user_by_chat_id_or_username


async def test_create_user(db_session):
    """Тест: создание нового пользователя."""

    tg_data = {
        "chat_id": 122333,
        "username": "newuser",
        "first_name": "New",
        "last_name": "User",
    }

    user = await get_or_create_user(db_session, tg_data)

    assert user.id is not None
    assert user.telegram_chat_id == "122333"
    assert user.username == "newuser"
    assert user.first_name == "New"
    assert user.is_active is True


async def test_get_existing_user(db_session, test_user):
    """Тест: получение существующего пользователя."""
    # test_user - это фикстура, уже созданный пользователь
    tg_data = {
        "chat_id": test_user.telegram_chat_id,
        "username": "someother",
    }

    user = await get_or_create_user(db_session, tg_data)

    # Проверяем, что вернулся тот же пользователь
    assert user.id == test_user.id
    assert user.username == test_user.username  # Не перезаписался


async def test_get_user_by_chat_id(db_session, test_user):
    """Тест: поиск пользователя по chat_id."""
    user = await get_user_by_chat_id_or_username(
        db_session,
        chat_id=test_user.telegram_chat_id
    )

    assert user is not None
    assert user.id == test_user.id


async def test_get_user_not_found(db_session):
    """Тест: поиск несуществующего пользователя."""
    user = await get_user_by_chat_id_or_username(
        db_session,
        chat_id="999999999"
    )

    assert user is None
