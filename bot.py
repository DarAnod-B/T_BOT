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

file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.DEBUG,
    encoding="utf-8",
    handlers=[file_handler, console_handler],
)
    

# Инициализация бота
logging.info("Инициализация бота...")
try:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    logging.info("Бот и диспетчер успешно инициализированы.")
except Exception as e:
    logging.critical(f"Ошибка при инициализации бота: {e}")
    raise

# Регистрация роутера
try:
    dp.include_router(router)
    logging.info("Роутер успешно зарегистрирован.")
except Exception as e:
    logging.error(f"Ошибка при регистрации роутера: {e}")
    raise


async def main():
    logging.info("Запуск основной функции...")
    try:

        # Установка команд бота
        await bot.set_my_commands(
            [
                BotCommand(command="/start", description="Запустить бота"),
                BotCommand(command="/logs", description="Получить логи"),
            ]
        )
        logging.info("Команды бота успешно установлены.")
        
        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Критическая ошибка в процессе работы бота: {e}")
    finally:
        # Закрытие соединения с ботом при завершении
        await bot.session.close()
        logging.info("Соединение с ботом закрыто.")


if __name__ == "__main__":
    logging.info("Запуск бота через __main__...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Бот остановлен вручную (KeyboardInterrupt).")
    except Exception as e:
        logging.error(f"Необработанное исключение: {e}")
    finally:
        logging.info("Бот завершил работу.")

        