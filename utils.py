import os
import logging
import uuid
from orchestrator import run_container
from typing import Callable
from aiogram.types import Message

# Глобальные пути
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

# Создаем директорию для логов, если ее нет
os.makedirs(LOG_DIR, exist_ok=True)


def get_log_file() -> str:
    """Создает уникальный файл для логов текущего запроса."""
    log_filename = f"log_{uuid.uuid4()}.log"
    return os.path.join(LOG_DIR, log_filename)


def save_links_to_file(links, filename="links.txt") -> str:
    """Сохраняет ссылки в файл."""
    links_path = os.path.join(DATA_DIR, "table", filename)
    os.makedirs(os.path.dirname(links_path), exist_ok=True)
    with open(links_path, "w") as file:
        file.write("\n".join(links))
    return links_path

async def handle_error(e, message, status_callback, specific_message=None):
    """Обработка ошибок с обновлением статуса и логированием."""
    error_message = specific_message or f"❌ Ошибка при выполнении: {str(e)}"
    await update_status(message, error_message, status_callback)
    logging.error(error_message, exc_info=True)

async def update_status(
    message: Message, log_message: str, status_callback: Callable[[str], None] = None
):
    """Отправляет сообщение в Telegram и логирует."""
    if status_callback:
        status_callback(log_message)
    logging.info(log_message)
    await message.answer(log_message)


async def process_links_with_orchestrator(
    links,
    log_file: str,
    message: Message,
    client_name: str = None,
    status_callback: Callable[[str], None] = None,
):
    """Обрабатывает ссылки с помощью оркестратора и сохраняет логи."""
    # Настраиваем логирование для текущего запроса
    logging.basicConfig(filename=log_file, level=logging.INFO)

    # Сохраняем ссылки в файл
    save_links_to_file(links)

    try:
        stages = [
            (
                "🔄 Этап 1/4: Парсинг данных...",
                "parser_image",
                {
                    "INPUT_PATH": "/app/data/table/links.txt",
                    "OUTPUT_PATH": "/app/data/table/data.csv",
                },
                "✅ Парсинг завершен",
            ),
            (
                "🔄 Этап 2/4: Переписывание текста...",
                "rewriter_image",
                {
                    "INPUT_PATH": "/app/data/table/data.csv",
                    "MAX_SYMBOL": "995",
                    "COLUMN_NAME": "Описание",
                },
                "✅ Переписывание завершено",
            ),
            (
                "🔄 Этап 3/4: Создание презентации...",
                "presentation_image",
                {
                    "INPUT_PATH": "/app/data/table/data.csv",
                    "OUTPUT_PATH": "/app/data/presentation/output/",
                    "TEMPLATE": "/app/data/presentation/template/Упрощенный_белый_шаблон.pptx",
                },
                "✅ Создание презентации завершено",
            ),
            (
                "🔄 Этап 4/4: Обработка таблиц...",
                "sheet_tools_image",
                {
                    "INPUT_PATH": "/app/data/table/data.csv",
                    "PRESENTATION_PATH": "/app/data/presentation/output/",
                    "CONFIG_PATH": "/app/data/config.env",
                    "CLIENT_NAME":client_name,
                },
                "✅ Обработка таблиц завершена",
            ),
        ]

        logs = []
        await update_status(message, "📝 Начало обработки ссылок...", status_callback)

        for stage_info in stages:
            start_message, image_name, environment, end_message = stage_info
            await update_status(message, start_message, status_callback)
            stage_logs = run_container(image_name, environment=environment)
            logs.append(stage_logs)
            await update_status(message, end_message, status_callback)

        await update_status(
            message, "🎉 Все процессы успешно завершены!", status_callback
        )
        return logs
    except OSError as e:
        if e.winerror == 121:
            await handle_error(e, message, status_callback, 
                            specific_message="❌ Ошибка при выполнении, повторите запрос.")
        else:
            await handle_error(e, message, status_callback)
            raise RuntimeError("Ошибка при запуске оркестратора") from e

    except Exception as e:
        await handle_error(e, message, status_callback)
        raise RuntimeError("Ошибка при запуске оркестратора") from e





