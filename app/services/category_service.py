from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.user import User


async def create_cat(db: AsyncSession, user: User, name: str, ) -> Category:
    """Создает новую категорию."""
    # Проверяем, есть ли уже такая категория у пользователя
    query = select(Category).where(Category.user_id == user.id, Category.name == name)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        return existing  # Возвращаем существующую категорию

    cat = Category(name=name, user_id=user.id,)

    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def get_user_cats(db: AsyncSession, user_id: int) -> list[Category]:
    """Получить все категории пользователя."""
    query = select(Category).where(Category.user_id == user_id).order_by(Category.name)
    result = await db.execute(query)
    return result.scalars().all()  # .scalars() - преобразует каждую строку из кортежа в первый элемент этого кортежа
                                   # .all() - собирает все в список


async def get_cat_by_id(db: AsyncSession, category_id: int, user_id: int) -> Category | None:
    """Получить категорию по ID (с проверкой владельца)."""
    query = select(Category).where(Category.id == category_id, Category.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_cat(db: AsyncSession, category: Category, new_name: str) -> Category:
    """Обновляет название категории."""
    category.name = new_name
    await db.commit()
    await db.refresh(category)
    return category


async def delete_cat(db: AsyncSession, category: Category) -> None:
    """Удаляет категорию."""
    await db.delete(category)
    await db.commit()

