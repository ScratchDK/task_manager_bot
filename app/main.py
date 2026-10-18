import asyncio
from contextlib import asynccontextmanager
from app.core.celery import celery_app
from app.api.v1 import api_router

import redis.asyncio as redis
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI, Request, HTTPException

from app.bot import menu
from app.bot.dialogs import crud_cat, crud_task, task_callbacks, comment_processing, copy_message, task_pagination
from app.bot.handlers import start
from app.core.config import settings
from app.bot.middlewares.db import DbSessionMiddleware

from aiogram.types import Update

# Глобальные переменные для хранения клиента и хранилища (Для дальнейшего использования в других задачах)
redis_client = None
storage = None
# Для дальнейшего использования в webhook
bot = None
dp = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, storage, bot, dp
    # 1. Подключаемся к Redis
    redis_client = redis.from_url("redis://redis:6379/0")
    storage = RedisStorage(redis=redis_client)  # state: FSMContext обертка над хранилищем REDIS

    # 2. Создаём бота и диспетчер СРАЗУ с нужным хранилищем
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)  # Основной мозг бота, хранятся данные диалога

    # TODO: До подключения роутов?!!!
    # 2.1 Регистрируем middleware для ВСЕХ типов апдейтов
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    # 3. Подключаем хендлеры, диалоги и т.д.
    # Важен порядок обработчиков!!!
    dp.include_router(start.router)
    dp.include_router(crud_task.router)
    dp.include_router(crud_cat.router)

    dp.include_router(task_callbacks.router)  # TODO: Могут быть конфликты? 👇

    dp.include_router(task_pagination.router)

    dp.include_router(comment_processing.router)  # Новый
    dp.include_router(copy_message.router)  # Новый

    dp.include_router(menu.router)       # TODO: Могут быть конфликты? 👆

    # 4. Запускаем бота
    if settings.USE_WEBHOOK:
        # --- WEBHOOK ---
        webhook_url = f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET.get_secret_value(),
            drop_pending_updates=True,
        )
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        # --- POLLING ---
        asyncio.create_task(dp.start_polling(bot))
        # dp.start_polling(bot) - асинхронная корутина запускающая бесконечный цикл
        # asyncio.create_task() - добавляет корутину в event loop
        print("✅ Бот запущен в режиме polling")
    # 5. Отдаем управление FastAPI
    yield

    # 6. При выключении приложения закрываем сессию бота
    if settings.USE_WEBHOOK:
        await bot.delete_webhook()
    await storage.close()
    await redis_client.close()
    await bot.session.close()

app = FastAPI(
    title="Task Manager Bot API",
    lifespan=lifespan
)

# Подключаем API
app.include_router(api_router, prefix="/api/v1")


# @app.post(settings.WEBHOOK_PATH)
# async def webhook(request: Request):
#     """Эндпоинт для приёма апдейтов от Telegram."""
#     # Проверка секретного токена
#     secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
#     if secret_token != settings.WEBHOOK_SECRET.get_secret_value():
#         raise HTTPException(status_code=403, detail="Invalid secret token")
#
#     # Парсинг апдейта
#     update_data = await request.json()
#     update = Update.model_validate(update_data)
#
#     # Передача в aiogram
#     await dp.feed_update(bot, update)
#
#     return {"ok": True}


@app.get("/")
async def root():
    return {"message": "Task Manager Bot is running with FastAPI!"}
