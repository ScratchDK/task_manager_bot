from app.services.category_service import create_cat, get_user_cats, get_cat_by_id, update_cat, delete_cat


async def test_create_category(db_session, test_user):
    """Создание новой категории."""
    category = await create_cat(db_session, test_user, "Работа")

    assert category.id is not None
    assert category.name == "Работа"
    assert category.user_id == test_user.id


async def test_create_duplicate_category(db_session, test_user):
    """Попытка создать категорию с тем же именем."""
    cat1 = await create_cat(db_session, test_user, "Работа")
    cat2 = await create_cat(db_session, test_user, "Работа")

    assert cat1.id == cat2.id  # ← Та же категория


async def test_get_user_categories(db_session, test_user):
    """Получение всех категорий пользователя."""
    await create_cat(db_session, test_user, "Работа")
    await create_cat(db_session, test_user, "Личное")
    await create_cat(db_session, test_user, "Учёба")

    categories = await get_user_cats(db_session, test_user.id)

    assert len(categories) == 3
    names = [cat.name for cat in categories]
    assert "Работа" in names
    assert "Личное" in names
    assert "Учёба" in names


async def test_get_user_categories_empty(db_session, test_user):
    """Если у пользователя нет категорий — возвращается пустой список."""
    categories = await get_user_cats(db_session, test_user.id)

    assert categories == []


async def test_get_cat_by_id(db_session, test_user):
    """Получение категории по ID."""
    category = await create_cat(db_session, test_user, "Работа")

    found = await get_cat_by_id(db_session, category.id, test_user.id)

    assert found is not None
    assert found.id == category.id
    assert found.name == "Работа"


async def test_get_cat_by_id_wrong_user(db_session, test_user):
    """Попытка получить чужую категорию — возвращается None."""
    from app.models import User

    other_user = User(telegram_chat_id="999", is_active=True)
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    category = await create_cat(db_session, test_user, "Работа")

    # Пытаемся получить категорию от имени другого пользователя
    found = await get_cat_by_id(db_session, category.id, other_user.id)

    assert found is None


async def test_update_category(db_session, test_user):
    """Обновление названия категории."""
    category = await create_cat(db_session, test_user, "Работа")

    updated = await update_cat(db_session, category, "Работа и карьера")

    assert updated.name == "Работа и карьера"
    assert updated.id == category.id


async def test_delete_category(db_session, test_user):
    """Удаление категории."""
    category = await create_cat(db_session, test_user, "Работа")
    category_id = category.id

    await delete_cat(db_session, category)

    # Проверяем, что категории больше нет
    found = await get_cat_by_id(db_session, category_id, test_user.id)
    assert found is None
