from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
import logging
import re

from ..utils import process_links_with_orchestrator, get_log_file

URL_REGEX = re.compile(
    r"^(https?:\/\/)?"  # Протокол (http или https)
    r"([\da-z\.-]+)\.([a-z\.]{2,6})"  # Домен
    r"([\/\w\.-]*)*\/?$"  # Путь
)
# Папка, где хранятся презентации
PRESENTATION_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "presentation", "output")
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
    waiting_for_client_name = State()  # Ожидание имени клиента


# Память для хранения состояний (можно заменить на Redis или другой storage)
storage = MemoryStorage()

# Команда для выхода из текущего состояния
EXIT_COMMAND = "выход"

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
        "👤 Пожалуйста, укажите имя клиента, для которого создаются презентации."
    )
    # Устанавливаем состояние ожидания имени клиента
    await state.set_state(LinkStates.waiting_for_client_name)

# Обработчик для отмены любого состояния
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


@router.message(LinkStates.waiting_for_client_name)
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
        "🔗 Теперь отправьте список ссылок (каждая ссылка с новой строки)."
    )
    await state.set_state(LinkStates.waiting_for_links)


@router.message(LinkStates.waiting_for_links)
async def handle_links(message: Message, state: FSMContext):
    """Обработчик сообщений с ссылками в состоянии ожидания."""
    # Получаем ссылки из сообщения
    links = message.text.strip().splitlines()
    links_clean = [link for link in links if link not in ["", "\n"]]

    # Проверяем, что каждая строка является ссылкой
    invalid_links = [link for link in links_clean if not URL_REGEX.match(link)]

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
        f"Начинаю обработку ссылок для клиента: {client_name}"
    )

    log_file = get_log_file()  # Уникальный файл для логов

    try:
        # Обрабатываем ссылки
        output_status = await process_links_with_orchestrator(
            links, log_file, message, client_name
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
                        await message.answer_document(
                            document
                        )  # Отправляем документ
                        logging.info(f"Файл отправлен: {file_name}")
                    except Exception as e:
                        logging.error(
                            f"Ошибка при отправке файла: {e}", exc_info=True
                        )
                else:
                    logging.warning(f"Объект {file_path} не является файлом.")
            await message.answer("Презентации отправлены!")

        else:
            await message.answer(
                "Произошла ошибка при обработке ссылок на этапе парсинга и создания презентации, поэтому презентации не отправлены."
            )
            logging.warning(
                "Произошла ошибка при обработке ссылок на этапе парсинга и создания презентации , поэтому презентации не отправлены."
            )

    except Exception as e:
        logging.error(f"Ошибка при обработке ссылок: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке ссылок.")

    # Сбрасываем состояние
    await state.clear()


@router.message(Command("logs"))
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
        await message.answer_document(
            FSInputFile(last_log_file)
        )  # Отправляем лог
    else:
        await message.answer("Логи недоступны.")