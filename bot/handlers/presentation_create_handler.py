from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import os
import logging

from ..utils.utils import process_links_with_orchestrator, get_log_file

URL_REGEX = re.compile(
    r"^(https?:\/\/)?"  # Протокол (http или https)
    r"([\da-z\.-]+)\.([a-z\.]{2,6})"  # Домен
    r"([\/\w\.-]*)*\/?$"  # Путь
)

router = Router()


class LinkStates(StatesGroup):
    waiting_for_links = State()
    waiting_for_client_name = State()  # Ожидание имени клиента

@router.message(Command("links_to_presentations"))
async def links_to_presentations_command(message: Message, state: FSMContext):
    """Обработчик команды /links_to_presentations."""
    await message.answer(
        "👤 Пожалуйста, укажите имя клиента, для которого создаются презентации."
    )
    await state.set_state(LinkStates.waiting_for_client_name)

@router.message(LinkStates.waiting_for_client_name)
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

@router.message(LinkStates.waiting_for_links)
async def handle_links(message: Message, state: FSMContext):
    """Обработчик сообщений с ссылками в состоянии ожидания."""
    links = message.text.strip().splitlines()
    links_clean = [link for link in links if link not in ["", "\n"]]

    invalid_links = [link for link in links_clean if not URL_REGEX.match(link)]

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

    log_file = get_log_file()

    try:
        output_status = await process_links_with_orchestrator(
            links, log_file, message, client_name
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
                "Произошла ошибка при обработке ссылок."
            )

    except Exception as e:
        await message.answer("Произошла ошибка при обработке ссылок.")

    await state.clear()