from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
import logging

# Создаем роутер
start_router = Router()


@start_router.message(Command("start"))
async def start(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Вот список доступных команд:\n"
        "/links_to_presentations - Отправь ссылки, чтобы создать презентации.\n"
        "/logs - Получить файл логов последнего запроса.\n"
        "/cancel - Отменить текущее действие. (если, например указаны неверные данные во время создания презентации, можно его отменить)"
    )
