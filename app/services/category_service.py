from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.category import Category
from app.models.user import User


async def create_cat(db: AsyncSession, user: User, name: str, ) -> Category:
    """Создает новую категорию."""
    # Проверяем, есть ли уже такая категория у пользователя
    query = select(Category).where(
        Category.user_id == user.id,
        Category.name == name
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        return existing  # Возвращаем существующую категорию

    cat = Category(
        name=name,
        user_id=user.id,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def get_user_categories(db: AsyncSession, user_id: int) -> list[Category]:
    """Получить все категории пользователя."""
    query = select(Category).where(Category.user_id == user_id).order_by(Category.name)
    result = await db.execute(query)
    return result.scalars().all()  # .scalars() - преобразует каждую строку из кортежа в первый элемент этого кортежа
                                   # .all() - собирает все в список

