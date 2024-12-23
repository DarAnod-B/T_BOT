from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import router  # Импортируем роутер
import asyncio
import logging
from imp import reload
import datetime


now = datetime.datetime.now()

LOG_FILENAME = f"./logs/bot_{now.strftime('%Y%m%d_%H-%M-%S')}.log"

reload(logging)
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, encoding="utf-8")


# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Регистрация роутера
dp.include_router(router)


# Асинхронная функция для запуска бота
async def main():
    # Установка команд бота
    await bot.set_my_commands(
        [
            BotCommand(command="/start", description="Запустить бота"),
            BotCommand(command="/logs", description="Получить логи"),
        ]
    )
    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
