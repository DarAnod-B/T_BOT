import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config.config import BOT_TOKEN
from bot.handlers import router
from bot.orchestrator import orchestrator
from bot.logger import setup_logger 


# Настраиваем логгер
logger = setup_logger()


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