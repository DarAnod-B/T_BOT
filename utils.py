import os
import logging
import uuid
from typing import Callable, List, Tuple, Dict
from aiogram.types import Message
from .orchestrator import run_container

# Глобальные пути
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
STAGES_OF_PRESENTATION_CREATION = [1, 2, 3, 4]

# Создаем директорию для логов, если ее нет
os.makedirs(LOG_DIR, exist_ok=True)


def get_log_file() -> str:
    """Создает уникальный файл для логов текущего запроса."""
    log_filename = f"log_{uuid.uuid4()}.log"
    return os.path.join(LOG_DIR, log_filename)


def save_links_to_file(links: List[str], filename="links.txt") -> str:
    """Сохраняет список ссылок в файл."""
    links_path = os.path.join(DATA_DIR, "table", filename)
    os.makedirs(os.path.dirname(links_path), exist_ok=True)
    with open(links_path, "w") as file:
        file.write("\n".join(links))
    return links_path


async def handle_error(
    e: Exception, message: Message, status_callback: Callable[[str], None] = None, specific_message: str = None
):
    """Обработка ошибок с логированием и отправкой сообщения в Telegram."""
    error_message = specific_message or f"❌ Ошибка при выполнении: {str(e)}"
    detailed_error = f"‼️ *Произошла ошибка:*\n```\n{str(e)}\n```"

    logging.error(error_message, exc_info=True)

    # Обновляем статус через callback (если он есть)
    if status_callback:
        status_callback(error_message)

    # Отправляем сообщение в Telegram
    await message.answer(detailed_error, parse_mode="MarkdownV2")


async def update_status(
    message: Message, log_message: str, status_callback: Callable[[str], None] = None
):
    """Отправляет сообщение в Telegram и логирует."""
    if status_callback:
        status_callback(log_message)
    logging.info(log_message)
    await message.answer(log_message)


def get_processing_stages(client_name: str = None) -> List[Tuple[str, str, Dict[str, str], str]]:
    """Возвращает список этапов для обработки ссылок."""
    return [
        (
            "🔄 Этап 1/5: Парсинг данных...",
            "cian_deep_page_parser",
            {
                "INPUT_PATH": "/app/data/table/links.txt",
                "OUTPUT_PATH": "/app/data/table/data.csv",
            },
            "✅ Парсинг завершен",
        ),
        (
            "🔄 Этап 2/5: Переписывание текста...",
            "rewriter_image",
            {
                "INPUT_PATH": "/app/data/table/data.csv",
                "MAX_SYMBOL": "995",
                "COLUMN_NAME": "Описание",
            },
            "✅ Переписывание завершено",
        ),
        (
            "🔄 Этап 3/5: Обработка изображений...",
            "image_processor",
            {
                "INPUT_PATH": "/app/data/table/data.csv",
                "MASK_DIR_PATH": "/app/data/mask/",
                "BASE_IMAGE_DIR_PATH":  "/app/data/presentation/pic/",
            },
            "✅ Обработка таблиц завершена",
        ),
        (
            "🔄 Этап 4/5: Создание презентации...",
            "presentation_image",
            {
                "INPUT_PATH": "/app/data/table/data.csv",
                "OUTPUT_PATH": "/app/data/presentation/output/",
                "PIC_PATH": "/app/data/presentation/pic/",
                "TEMPLATE_PATH": "/app/data/presentation/template/Упрощенный_белый_шаблон.pptx",
            },
            "✅ Создание презентации завершено",
        ),
        (
            "🔄 Этап 5/5: Обработка таблиц...",
            "sheet_tools_image",
            {
                "INPUT_PATH": "/app/data/table/data.csv",
                "PRESENTATION_PATH": "/app/data/presentation/output/",
                "CONFIG_PATH": "/app/data/config/config.env",
                "CLIENT_NAME": client_name,
            },
            "✅ Обработка таблиц завершена",
        ),
    ]


async def process_stage(
    stage_info: Tuple[str, str, Dict[str, str], str], message: Message, status_callback: Callable[[str], None]
) -> Tuple[bool, str]:
    """Обрабатывает один этап с помощью контейнера."""
    start_message, image_name, environment, end_message = stage_info
    await update_status(message, start_message, status_callback)

    stage_logs, exit_code = run_container(image_name, environment=environment)

    if exit_code != 0:
        return False, stage_logs

    await update_status(message, end_message, status_callback)
    return True, stage_logs


async def process_links_with_orchestrator(
    links: List[str], log_file: str, message: Message, client_name: str = None, status_callback: Callable[[str], None] = None
) -> bool:
    """Обрабатывает ссылки с помощью оркестратора и сохраняет логи."""
    logging.basicConfig(filename=log_file, level=logging.INFO)
    save_links_to_file(links)

    try:
        stages = get_processing_stages(client_name)
        logs = []

        await update_status(message, "📝 Начало обработки ссылок...", status_callback)

        for stage_index, stage_info in enumerate(stages, start=1):
            success, stage_logs = await process_stage(stage_info, message, status_callback)
            logs.append(stage_logs)
            if not success:
                await handle_error(
                    f"Ошибка при выполнении этапа: {stage_info[0]}", message, status_callback
                )
                if stage_index not in STAGES_OF_PRESENTATION_CREATION:
                    return True
                else:
                    return False

        await update_status(message, "🎉 Все процессы успешно завершены!", status_callback)
        return True
    except OSError as e:
        if getattr(e, "winerror", None) == 121:
            await handle_error(
                e, message, status_callback, specific_message="❌ Ошибка при выполнении, повторите запрос."
            )
        else:
            await handle_error(e, message, status_callback)
        return False
    except Exception as e:
        await handle_error(e, message, status_callback)
        return False