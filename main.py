import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
import database as db
from handlers import router, check_learning_done

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)


async def scheduler():
    """Раз в минуту проверяет, не закончилось ли обучение."""
    while True:
        try:
            await check_learning_done(bot)
        except Exception as e:
            print(f"Scheduler error: {e}")
        await asyncio.sleep(60)


async def main():
    await db.init_db()
    print("База данных готова")
    asyncio.create_task(scheduler())
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
