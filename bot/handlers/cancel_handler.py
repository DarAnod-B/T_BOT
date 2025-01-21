from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

logger = logging.getLogger(__name__)


# Создаем роутер
cancel_router = Router()

# Команда для выхода из текущего состояния
EXIT_COMMAND = "выход"


# Обработчик для отмены любого состояния
@cancel_router.message(Command("cancel"))
@cancel_router.message(F.text.lower() == EXIT_COMMAND)
async def cancel(message: Message, state: FSMContext):
    """Позволяет пользователю отменить любое состояние."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    logging.info("Пользователь отменил действие.")
    await message.answer("Действие отменено.")

