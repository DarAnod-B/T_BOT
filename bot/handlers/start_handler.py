from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Вот список доступных команд:\n"
        "/links_to_presentations - Отправь ссылки, чтобы создать презентации.\n"
        "/logs - Получить файл логов последнего запроса."
    )