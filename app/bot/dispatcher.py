from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings

# TODO: И в main тоже. Исправить, удалить ненужное или слить вместе!!!
# Инициализация бота
bot = Bot(
    token=settings.BOT_TOKEN.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Хранилище для состояний (FSM)
storage = MemoryStorage()

# Диспетчер
dp = Dispatcher(storage=storage)
