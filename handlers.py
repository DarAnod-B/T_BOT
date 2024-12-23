from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from utils import process_links_with_orchestrator, get_log_file
import os
import logging
import re

URL_REGEX = re.compile(
    r"^(https?:\/\/)?"  # Протокол (http или https)
    r"([\da-z\.-]+)\.([a-z\.]{2,6})"  # Домен
    r"([\/\w\.-]*)*\/?$"  # Путь
)
# Папка, где хранятся презентации
PRESENTATION_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "presentation", "output"
)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Создаем роутер
router = Router()


# Состояния для FSM
class LinkStates(StatesGroup):
    waiting_for_links = State()


# Память для хранения состояний (можно заменить на Redis или другой storage)
storage = MemoryStorage()


@router.message(Command("start"))
async def start_command(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Вот список доступных команд:\n"
        "/links_to_presentations - Отправь ссылки, чтобы создать презентации.\n"
        "/logs - Получить файл логов последнего запроса."
    )


@router.message(Command("links_to_presentations"))
async def links_to_presentations_command(message: Message, state: FSMContext):
    """Обработчик команды /links_to_presentations."""
    await message.answer(
        "Отправь мне список ссылок (каждую ссылку с новой строки), и я создам презентации для тебя."
    )
    # Устанавливаем состояние "ожидание ссылок"
    await state.set_state(LinkStates.waiting_for_links)


@router.message(LinkStates.waiting_for_links)
async def handle_links(message: Message, state: FSMContext):
    """Обработчик сообщений с ссылками в состоянии ожидания."""
    # Получаем ссылки из сообщения
    links = message.text.strip().splitlines()

    # Проверяем, что каждая строка является ссылкой
    invalid_links = [link for link in links if not URL_REGEX.match(link)]

    if invalid_links:
        # Если есть некорректные ссылки, запросить повторный ввод
        await message.answer(
            "Некоторые строки не являются корректными ссылками. Пожалуйста, отправьте только ссылки. \n\n"
            f"Некорректные строки: \n{chr(10).join(invalid_links)}"
        )
        return

    if not links:
        await message.answer("Пожалуйста, отправьте хотя бы одну ссылку.")
        return

    await message.answer("Обрабатываю ссылки, это может занять некоторое время...")

    log_file = get_log_file()  # Уникальный файл для логов

    try:
        # Обрабатываем ссылки
        await process_links_with_orchestrator(links, log_file, message)

        await message.answer("Обработка завершена. Отправляю презентации...")

        # Отправляем все файлы презентаций из папки
        for file_name in os.listdir(PRESENTATION_DIR):
            file_path = os.path.join(PRESENTATION_DIR, file_name)
            if os.path.isfile(file_path):
                try:
                    document = FSInputFile(file_path)
                    await message.answer_document(document)  # Отправляем документ
                    logging.info(f"Файл отправлен: {file_name}")
                except Exception as e:
                    logging.error(f"Ошибка при отправке файла: {e}", exc_info=True)
            else:
                logging.warning(f"Объект {file_path} не является файлом.")
        await message.answer("Презентации отправлены!")

    except Exception as e:
        logging.error(f"Ошибка при обработке ссылок: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке ссылок.")

    # Сбрасываем состояние
    await state.clear()


@router.message(Command("logs"))
async def send_logs(message: Message):
    """Отправляем логи последнего запроса."""
    log_files = sorted(
        [f for f in os.listdir("logs") if f.endswith(".log")],
        key=lambda x: os.path.getmtime(os.path.join("logs", x)),
        reverse=True,
    )

    if log_files:
        last_log_file = os.path.join("logs", log_files[0])
        await message.answer_document(FSInputFile(last_log_file))  # Отправляем лог
    else:
        await message.answer("Логи недоступны.")
