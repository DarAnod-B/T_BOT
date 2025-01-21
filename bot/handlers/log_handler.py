from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
import os
import logging

logger = logging.getLogger(__name__)
 
# Создаем роутер
log_router = Router()


@log_router.message(Command("logs"))
async def send_logs(message: Message):
    """Отправляем логи последнего запроса."""
    log_path = os.path.join(os.path.dirname(__file__), "..","logs")
    log_files = sorted(
        [os.path.join(log_path, f) for f in os.listdir(log_path) if f.endswith(".log")],
        key=lambda x: os.path.getmtime(os.path.join("logs", x)),
        reverse=True,
    )

    if log_files:
        last_log_file = os.path.join("logs", log_files[0])
        logger.info(f"Отправляем лог {last_log_file}")
        await message.answer_document(
            FSInputFile(last_log_file)
        )  # Отправляем лог
    else:
        logger.info("Логи недоступны.")
        await message.answer("Логи недоступны.")