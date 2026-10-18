import asyncio
from aiogram import Bot
from app.core.config import settings

async def main():
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook удалён")
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
