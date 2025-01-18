from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()

EXIT_COMMAND = "выход"

@router.message(Command("cancel"))
@router.message(F.text.lower() == EXIT_COMMAND)
async def cancel_handler(message: Message, state: FSMContext):
    """Позволяет пользователю отменить любое состояние."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного действия для отмены.")
        return

    await state.clear()
    await message.answer("Действие отменено.")