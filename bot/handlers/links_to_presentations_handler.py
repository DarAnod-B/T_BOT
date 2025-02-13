import os
import re
import logging
import asyncio
from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.utils.presentation_handler import process_links_with_orchestrator

logger = logging.getLogger(__name__)

# Регулярное выражение для валидации ссылок
URL_REGEX_CIAN = re.compile(
    r"^(https?:\/\/)?([\w-]+\.)?cian\.ru([\/\w\.\-\?&=%]*)?$",
    re.IGNORECASE
)

# Путь к папке с презентациями
PRESENTATION_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "presentation", "output")
)

# Создаем роутер
links_to_presentations_router = Router()


# Состояния FSM
class LinkStates(StatesGroup):
    waiting_for_links = State()
    waiting_for_client_name = State()
    processing_links = State()


@links_to_presentations_router.message(Command("links_to_presentations"))
async def links_to_presentations(message: Message, state: FSMContext):
    """Обработчик команды /links_to_presentations."""
    current_state = await state.get_state()

    if current_state:
        await message.answer(
            "❌ У вас уже есть активная задача! Дождитесь её завершения или используйте /cancel для отмены."
        )
        return

    await message.answer("👤 Пожалуйста, укажите имя клиента.\n\nЧтобы отменить задачу — используйте: /cancel")
    await state.set_state(LinkStates.waiting_for_client_name)


@links_to_presentations_router.message(LinkStates.waiting_for_client_name)
async def handle_client_name(message: Message, state: FSMContext):
    """Обрабатываем имя клиента и запрашиваем ссылки."""
    client_name = message.text.strip()
    if not client_name:
        await message.answer("⚠️ Пожалуйста, введите корректное имя клиента.")
        return

    await state.update_data(client_name=client_name)
    await message.answer("🔗 Теперь отправьте список ссылок (каждая ссылка с новой строки).\n\nЧтобы отменить задачу — используйте: /cancel")
    await state.set_state(LinkStates.waiting_for_links)


@links_to_presentations_router.message(LinkStates.waiting_for_links)
async def handle_links(message: Message, state: FSMContext):
    """Обрабатываем список ссылок и запускаем обработку."""
    try:
        links = [link.strip() for link in message.text.splitlines() if link.strip()]
        invalid_links = [link for link in links if not URL_REGEX_CIAN.match(link)]

        if invalid_links:
            await message.answer(
                "⚠️ Некоторые строки не являются корректными ссылками. Пожалуйста, отправьте только ссылки.\n\n"
                f"Некорректные строки:\n{chr(10).join(invalid_links)}"
            )
            return

        if not links:
            await message.answer("⚠️ Пожалуйста, отправьте хотя бы одну ссылку.")
            return

        data = await state.get_data()
        client_name = data.get("client_name")
        if not client_name:
            await message.answer("🚨 Ошибка! Пожалуйста, начните с указания имени клиента.")
            return

        await message.answer(f"🔄 Начинаю обработку ссылок для клиента: {client_name}\n\n⏳ Пожалуйста, подождите...")

        await state.set_state(LinkStates.processing_links)

        # Запускаем обработку ссылок в отдельной задаче
        asyncio.create_task(process_links_task(links, message, client_name, state))

    except Exception as e:
        logger.error(f"Ошибка при обработке ссылок: {e}", exc_info=True)
        await message.answer("🚨 Произошла критическая ошибка!")
        await state.clear()


async def process_links_task(links, message, client_name, state: FSMContext):
    """Фоновая задача для обработки ссылок и отправки файлов."""
    try:
        output_status = await process_links_with_orchestrator(links, message, client_name)

        if output_status:
            await message.answer("✅ Обработка завершена. Отправляю презентации...")

            files_sent = 0
            for file_name in os.listdir(PRESENTATION_DIR):
                file_path = os.path.join(PRESENTATION_DIR, file_name)
                if os.path.isfile(file_path):
                    try:
                        document = FSInputFile(file_path)
                        await message.answer_document(document)
                        files_sent += 1
                        logger.info(f"Файл отправлен: {file_name}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке файла {file_name}: {e}", exc_info=True)

            if files_sent == 0:
                await message.answer("⚠️ Не найдено файлов презентаций. Возможно, произошла ошибка.")

        else:
            await message.answer("🚨 Ошибка при обработке ссылок. Презентации не отправлены.")

    except Exception as e:
        logger.error(f"Ошибка в процессе обработки ссылок: {e}", exc_info=True)
        await message.answer("🚨 Критическая ошибка во время обработки!")

    finally:
        await state.clear()