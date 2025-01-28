import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.config import BOT_TOKEN
from bot.handlers import router
from bot.orchestrator import orchestrator

# Настройка логирования
LOG_FILENAME = f"logs/bot_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"

# Заменяем basicConfig на явную настройку корневого логгера
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s")

file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Убедитесь, что обработчики не дублируются
if not root_logger.hasHandlers():
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="/start", description="Начать работу с ботом"),
    BotCommand(command="/links_to_presentations", description="Создать презентации из ссылок"),
    BotCommand(command="/logs", description="Получить логи"),
    BotCommand(command="/cancel", description="Отменить текущее действие"),
]

async def init_bot() -> tuple[Bot, Dispatcher]:
    logger.info("Инициализация бота...")
    try:
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=MemoryStorage())
        logger.info("Бот и диспетчер успешно инициализированы.")
        return bot, dp
    except Exception as e:
        logger.critical(f"Ошибка при инициализации: {e}")
        raise

async def main():
    logger.info("Запуск бота...")
    
    # Инициализируем оркестратор
    await orchestrator.initialize()
    
    bot, dp = await init_bot()
    dp.include_router(router)

    try:
        await bot.set_my_commands(BOT_COMMANDS)
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка в процессе работы бота: {e}")
    finally:
        await orchestrator.shutdown()
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