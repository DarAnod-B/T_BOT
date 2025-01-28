from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import logging
import re

from bot.utils import process_links_with_orchestrator

logger = logging.getLogger(__name__)

URL_REGEX_CIAN = re.compile(
    r"^(https?:\/\/)?([\w-]+\.)?cian\.ru([\/\w\.\-\?&=%]*)?$",
    re.IGNORECASE
)

# Папка, где хранятся презентации
PRESENTATION_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "presentation", "output")
)

# Создаем роутер
links_to_presentations_router = Router()


# Состояния для FSM
class LinkStates(StatesGroup):
    waiting_for_links = State()
    waiting_for_client_name = State()  # Ожидание имени клиента
    processing_links = State()  # Процесс обработки ссылок


@links_to_presentations_router.message(Command("links_to_presentations"))
async def links_to_presentations(message: Message, state: FSMContext):
    """Обработчик команды /links_to_presentations."""
    current_state = await state.get_state()

    # Проверяем, есть ли активная задача у пользователя
    if current_state and current_state.startswith("LinkStates"):
        await message.answer(
            "❌ У вас уже есть активная задача! \n"
            "Дождитесь завершения текущей задачи.\n"
        )
        return

    await message.answer(
        "👤 Пожалуйста, укажите имя клиента.\n\n"
        "Чтобы отменить задачу — используйте: /cancel"
    )
    await state.set_state(LinkStates.waiting_for_client_name)


@links_to_presentations_router.message(LinkStates.waiting_for_client_name)
async def handle_client_name(message: Message, state: FSMContext):
    """Обрабатываем имя клиента и запрашиваем ссылки."""
    client_name = message.text.strip()

    if not client_name:
        await message.answer("Пожалуйста, введите корректное имя клиента.")
        return

    # Сохраняем имя клиента в состояние FSM
    await state.update_data(client_name=client_name)

    # Переходим к запросу ссылок
    await message.answer(
        "🔗 Теперь отправьте список ссылок (каждая ссылка с новой строки).\n\n"
        "Чтобы отменить задачу — используйте: /cancel"
    )
    await state.set_state(LinkStates.waiting_for_links)


@links_to_presentations_router.message(LinkStates.waiting_for_links)
async def handle_links(message: Message, state: FSMContext):
    """Обработчик сообщений с ссылками в состоянии ожидания."""
    try:
        # Получаем ссылки из сообщения
        links = message.text.strip().splitlines()
        links_clean = [link for link in links if link not in ["", "\n"]]

        # Проверяем, что каждая строка является ссылкой
        invalid_links = [link for link in links_clean if not URL_REGEX_CIAN.match(link)]

        if invalid_links:
            # Если есть некорректные ссылки, запросить повторный ввод
            await message.answer(
                "Некоторые строки не являются корректными ссылками. Пожалуйста, отправьте только ссылки. \n\n"
                f"Некорректные строки: \n{chr(10).join(invalid_links)}"
            )
            return

        if not links_clean:
            await message.answer("Пожалуйста, отправьте хотя бы одну ссылку.")
            return

        data = await state.get_data()
        client_name = data.get("client_name")

        if not client_name:
            await message.answer(
                "Произошла ошибка. Пожалуйста, начните с указания имени клиента."
            )
            return

        await message.answer(
            f"Начинаю обработку ссылок для клиента: {client_name}\n\n"
            f"⚠️ Пожалуйста, дождитесь завершения обработки — отмена на этом этапе невозможна."
        )

        # Устанавливаем состояние обработки ссылок
        await state.set_state(LinkStates.processing_links)

        # Обрабатываем ссылки
        output_status = await process_links_with_orchestrator(
            links, message, client_name
        )
        if output_status:
            await message.answer(
                "Обработка завершена. Отправляю презентации..."
            )

            # Отправляем все файлы презентаций из папки
            for file_name in os.listdir(PRESENTATION_DIR):
                file_path = os.path.join(PRESENTATION_DIR, file_name)
                if os.path.isfile(file_path):
                    try:
                        document = FSInputFile(file_path)
                        await message.answer_document(document)  # Отправляем документ
                        logger.info(f"Файл отправлен: {file_name}")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке файла: {e}", exc_info=True)
                else:
                    logger.warning(f"Объект {file_path} не является файлом.")
            await message.answer("Презентации отправлены!")

        else:
            error_processing_message = (
                "Произошла ошибка при обработке ссылок на этапе парсинга и создания презентации, поэтому презентации не отправлены."
            )
            await message.answer(error_processing_message)
            logger.warning(error_processing_message)

    except Exception as e:
        logger.error(f"Ошибка при обработке ссылок: {e}", exc_info=True)
        await message.answer("🚨 Произошла критическая ошибка!")
    finally:
        # Всегда сбрасываем состояние, даже если была ошибка
        await state.clear()