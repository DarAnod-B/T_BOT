from aiogram import Router
<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
========
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py
import os
import logging

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
from bot.utils import process_links_with_orchestrator 
========
from ..utils.utils import process_links_with_orchestrator, get_log_file
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py

logger = logging.getLogger(__name__)

URL_REGEX_CIAN = re.compile(
    r"^(https?:\/\/)?([\w-]+\.)?cian\.ru([\/\w\.\-\?&=%]*)?$",
    re.IGNORECASE
)

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
# Создаем роутер
links_to_presentations_router  = Router()
========
router = Router()
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py


class LinkStates(StatesGroup):
    waiting_for_links = State()
    waiting_for_client_name = State()  # Ожидание имени клиента

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py


@links_to_presentations_router .message(Command("links_to_presentations"))
async def links_to_presentations(message: Message, state: FSMContext):
========
@router.message(Command("links_to_presentations"))
async def links_to_presentations_command(message: Message, state: FSMContext):
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py
    """Обработчик команды /links_to_presentations."""
    await message.answer(
        "👤 Пожалуйста, укажите имя клиента, для которого создаются презентации."
    )
    await state.set_state(LinkStates.waiting_for_client_name)

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py

@links_to_presentations_router.message(LinkStates.waiting_for_client_name)
========
@router.message(LinkStates.waiting_for_client_name)
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py
async def handle_client_name(message: Message, state: FSMContext):
    """Обрабатываем имя клиента и запрашиваем ссылки."""
    client_name = message.text.strip()

    if not client_name:
        await message.answer("Пожалуйста, введите корректное имя клиента.")
        return

    await state.update_data(client_name=client_name)
    await message.answer(
        "🔗 Теперь отправьте список ссылок (каждая ссылка с новой строки)."
    )
    await state.set_state(LinkStates.waiting_for_links)

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py

@links_to_presentations_router.message(LinkStates.waiting_for_links)
========
@router.message(LinkStates.waiting_for_links)
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py
async def handle_links(message: Message, state: FSMContext):
    """Обработчик сообщений с ссылками в состоянии ожидания."""
    links = message.text.strip().splitlines()
    links_clean = [link for link in links if link not in ["", "\n"]]

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
    # Проверяем, что каждая строка является ссылкой
    invalid_links = [link for link in links_clean if not URL_REGEX_CIAN.match(link)]
========
    invalid_links = [link for link in links_clean if not URL_REGEX.match(link)]
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py

    if invalid_links:
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

<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
========
    log_file = get_log_file()
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py

    try:
        output_status = await process_links_with_orchestrator(
            links, message, client_name
        )
        if output_status:
            await message.answer(
                "Обработка завершена. Отправляю презентации..."
            )
            for file_name in os.listdir(PRESENTATION_DIR):
                file_path = os.path.join(PRESENTATION_DIR, file_name)
                if os.path.isfile(file_path):
                    try:
                        document = FSInputFile(file_path)
                        await message.answer_document(
                            document
                        )  # Отправляем документ
                        logger.info(f"Файл отправлен: {file_name}")
                    except Exception as e:
                        logger.error(
                            f"Ошибка при отправке файла: {e}", exc_info=True
                        )
                else:
                    logger.warning(f"Объект {file_path} не является файлом.")
            await message.answer("Презентации отправлены!")
        else:
<<<<<<<< HEAD:bot/handlers/links_to_presentations_handler.py
            error_processing_message = r"Произошла ошибка при обработке ссылок на этапе парсинга и создания презентации, поэтому презентации не отправлены."
            await message.answer(error_processing_message)
            logger.warning(error_processing_message)

    except Exception as e:
        logger.error(f"Ошибка при обработке ссылок: {e}", exc_info=True)
        await message.answer("Произошла ошибка при обработке ссылок.")

    # Сбрасываем состояние
    await state.clear()
========
            await message.answer(
                "Произошла ошибка при обработке ссылок."
            )

    except Exception as e:
        await message.answer("Произошла ошибка при обработке ссылок.")

    await state.clear()
>>>>>>>> f59c74059746ba6f69d1bda8aeda7a56bf54167e:bot/handlers/presentation_create_handler.py
