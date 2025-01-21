import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from imp import reload

from .config.config import BOT_TOKEN
from bot.handlers import router

reload(logging)

# Настройка логирования
LOG_FILENAME = f"logs/bot_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",  # Добавляем %(name)s для идентификации источника логов
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Команды бота
BOT_COMMANDS = [
    BotCommand(command="/start", description="Начать работу с ботом"),
    BotCommand(command="/links_to_presentations", description="Создать презентации из ссылок"),
    BotCommand(command="/logs", description="Получить логи"),
    BotCommand(command="/cancel", description="Отменить текущее действие"),
]

# Функция инициализации бота
def init_bot() -> tuple[Bot, Dispatcher]:
    logger.info("Инициализация бота...")
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        logger.info("Бот и диспетчер успешно инициализированы.")
        return bot, dp
    except Exception as e:
        logger.critical(f"Ошибка при инициализации: {e}")
        raise

# Функция регистрации роутеров
def register_routers(dp: Dispatcher):
    try:
        dp.include_router(router)
        logger.info("Роутер успешно зарегистрирован.")
    except Exception as e:
        logger.error(f"Ошибка при регистрации роутеров: {e}")
        raise

# Основная асинхронная функция
async def main():
    logger.info("Запуск бота...")
    
    bot, dp = init_bot()
    register_routers(dp)

    try:
        # Установка команд бота
        await bot.set_my_commands(BOT_COMMANDS)
        logger.info("Команды бота успешно установлены.")

        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка в процессе работы бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта.")

if __name__ == "__main__":
    logger.info("Запуск приложения...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Бот остановлен вручную (KeyboardInterrupt).")
    except Exception as e:
        logger.error(f"Необработанное исключение: {e}")
    finally:
        logger.info("Бот завершил работу.")