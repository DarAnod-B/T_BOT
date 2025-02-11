import os
import logging
from typing import Callable, List, Tuple, Dict, Optional
from aiogram.types import Message
from bot.orchestrator import (
    orchestrator,
)  # Импортируем глобальный асинхронный оркестратор
import aiofiles

logger = logging.getLogger(__name__)

# Глобальные пути
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
STAGES_OF_PRESENTATION_CREATION = [1, 2, 3, 4]


async def save_links_to_file(links: List[str], filename: str = "links.txt") -> str:
    """Асинхронно сохраняет список ссылок в файл."""
    links_path = os.path.join(DATA_DIR, "table", filename)
    os.makedirs(os.path.dirname(links_path), exist_ok=True)

    # Используем асинхронную запись в файл
    try:
        async with aiofiles.open(links_path, "w") as file:
            await file.write("\n".join(links))
        return links_path
    except Exception as e:
        logger.error(f"Error saving links: {e}")
        raise


async def handle_error(
    e: Exception,
    message: Message,
    status_callback: Optional[Callable[[str], None]] = None,
    specific_message: Optional[str] = None,
):
    """Асинхронная обработка ошибок с логированием и отправкой сообщения."""
    error_message = specific_message or f"❌ Ошибка при выполнении: {str(e)}"
    detailed_error = f"‼️ *Произошла ошибка:*\n```\n{str(e)}\n```"

    logger.error(error_message, exc_info=True)

    if status_callback:
        # Асинхронный callback, если требуется
        await status_callback(error_message)

    await message.answer(detailed_error, parse_mode="MarkdownV2")


async def update_status(
    message: Message,
    log_message: str,
    status_callback: Optional[Callable[[str], None]] = None,
):
    """Асинхронное обновление статуса."""
    try:
        if status_callback:
            await status_callback(log_message)
        logger.info(log_message)
        await message.answer(log_message)
    except Exception as e:
        logger.error(f"Error updating status: {e}")


def get_processing_stages(
    client_name: Optional[str] = None,
) -> List[Tuple[str, str, Dict[str, str], str]]:
    """Генерация этапов обработки (синхронная функция, не требует изменений)."""
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
                "MAX_SYMBOL": "500",
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
                "BASE_IMAGE_DIR_PATH": "/app/data/presentation/pic/",
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
            "🔄 Этап 5/5: Отправка данных в Google таблицу...",
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
    stage_info: Tuple[str, str, Dict[str, str], str],
    message: Message,
    status_callback: Callable[[str], None],
) -> Tuple[bool, str]:
    """Асинхронная обработка одного этапа."""
    start_message, image_name, environment, end_message = stage_info

    try:
        await update_status(message, start_message, status_callback)

        # Асинхронный запуск контейнера
        logs, exit_code = await orchestrator.run_container(
            image_name, environment=environment
        )

        if exit_code != 0:
            error_msg = f"Этап завершился с ошибкой (код {exit_code})"
            await message.answer(f"```\n{logs[-4000:]}\n```", parse_mode="MarkdownV2")
            return False, logs

        await update_status(message, end_message, status_callback)
        return True, logs

    except Exception as e:
        logger.error(f"Stage error: {e}", exc_info=True)
        return False, str(e)


async def process_links_with_orchestrator(
    links: List[str],
    message: Message,
    client_name: Optional[str] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> bool:
    """Асинхронная обработка всех этапов."""
    try:
        await save_links_to_file(links)
        stages = get_processing_stages(client_name)
        logs = []

        await update_status(message, "📝 Начало обработки ссылок...", status_callback)

        for stage_index, stage_info in enumerate(stages, start=1):
            success, stage_logs = await process_stage(
                stage_info, message, status_callback
            )
            logs.append(stage_logs)

            if not success:
                error_msg = f"Ошибка на этапе {stage_index}: {stage_info[0]}"
                await handle_error(Exception(error_msg), message, status_callback)

                if stage_index not in STAGES_OF_PRESENTATION_CREATION:
                    return True
                return False

        await update_status(
            message, "🎉 Все процессы успешно завершены!", status_callback
        )
        return True

    except Exception as e:
        await handle_error(e, message, status_callback)
        return False
