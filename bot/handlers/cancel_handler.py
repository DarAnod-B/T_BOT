from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging
from bot.handlers.links_to_presentations_handler import LinkStates

logger = logging.getLogger(__name__)


# Создаем роутер
cancel_router = Router()


# Обработчик для отмены любого состояния
@cancel_router.message(Command("cancel"))  # Обрабатывает команду /cancel
async def cancel(message: Message, state: FSMContext):
    """Позволяет пользователю отменить любое состояние."""
    
    # Получаем текущее состояние FSM для пользователя
    current_state = await state.get_state()

    # Проверяем, находится ли пользователь в состоянии обработки ссылок
    if current_state == LinkStates.processing_links.state:
        # Если да, то отмена недоступна. Сообщаем об этом пользователю.
        await message.answer("⚠️ Невозможно отменить процесс, так как ссылки уже обрабатываются.")
        return

    # Если у пользователя нет активного состояния, сообщаем ему об этом
    elif current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    # Если состояние есть и не является состоянием обработки, очищаем его (отмена задачи)
    await state.clear()
    logging.info("Пользователь отменил действие.")  # Логируем факт отмены действия

    # Сообщаем пользователю, что действие было отменено
    await message.answer("Действие отменено.")
