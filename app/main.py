import asyncio
from contextlib import asynccontextmanager
from app.core.celery import celery_app

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI

from app.bot import menu
from app.bot.dialogs import crud_cat, crud_task, callbacks
from app.bot.handlers import start
from app.core.config import settings

# Глобальные переменные для хранения клиента и хранилища (Для дальнейшего использования в других задачах)
redis_client = None
storage = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, storage
    # 1. Подключаемся к Redis
    redis_client = redis.from_url("redis://redis:6379/0")
    storage = RedisStorage(redis=redis_client)

    # 2. Создаём бота и диспетчер СРАЗУ с нужным хранилищем
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)

    # 3. Подключаем хендлеры, диалоги и т.д.
    dp.include_router(start.router)
    dp.include_router(crud_task.router)
    dp.include_router(crud_cat.router)

    dp.include_router(callbacks.router)  # TODO: Могут быть конфликты? 👇

    dp.include_router(menu.router)  # TODO: Могут быть конфликты? 👆

    # 4. Запускаем бота
    asyncio.create_task(dp.start_polling(bot))

    # 5. Отдаем управление FastAPI
    yield

    # 6. При выключении приложения закрываем сессию бота
    await storage.close()
    await redis_client.close()
    await bot.session.close()

app = FastAPI(
    title="Task Manager Bot API",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {"message": "Task Manager Bot is running with FastAPI!"}
