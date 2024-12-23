import os
import logging
from orchestrator import run_container
import uuid

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

# Создаем директорию для логов, если ее нет
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_log_file():
    """Создает уникальный файл для логов текущего запроса."""
    log_filename = f"log_{uuid.uuid4()}.log"
    return os.path.join(LOG_DIR, log_filename)

def save_links_to_file(links, filename="links.txt"):
    """Сохраняет ссылки в файл."""
    links_path = os.path.join(DATA_DIR, "table", filename)
    with open(links_path, "w") as file:
        file.write("\n".join(links))
    return links_path

def process_links_with_orchestrator(links, log_file):
    """Обрабатывает ссылки с помощью оркестратора и сохраняет логи."""
    # Настраиваем логирование для текущего запроса
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),  # Логи пишутся в файл
            logging.StreamHandler()  # Логи также выводятся в консоль
        ]
    )

    # Сохраняем ссылки в файл
    save_links_to_file(links)

    try:
        # parser_logs = run_container(
        #     "parser_image",
        #     environment={
        #         "INPUT_PATH": "/app/data/table/links.txt",
        #         "OUTPUT_PATH": "/app/data/table/data.csv",
        #     },
        # )

        # rewriter_logs = run_container(
        #     "rewriter_image",
        #     environment={
        #         "INPUT_PATH": "/app/data/table/data.csv",
        #         "MAX_SYMBOL": "995",
        #         "COLUMN_NAME": "Описание",
        #     },
        # )

        # presentation_logs = run_container(
        #     "presentation_image",
        #     environment={
        #         "INPUT_PATH": "/app/data/table/data.csv",
        #         "OUTPUT_PATH": "/app/data/presentation/output/",
        #         "TEMPLATE": "/app/data/presentation/template/Упрощенный_белый_шаблон.pptx",  # Шаблон для презентации
        #     },
        # )

        sheet_tools_logs = run_container(
            "sheet_tools_image",
            environment={
                "INPUT_PATH": "/app/data/table/data.csv",
                "PRESENTATION_PATH": "/app/data/presentation/output/",
            },
        )

        logging.info("Все процессы завершены успешно.")
        # return parser_logs, rewriter_logs, presentation_logs, sheet_tools_logs
    except Exception as e:
        logging.error("Ошибка при запуске оркестратора.", exc_info=True)
        raise RuntimeError("Ошибка при запуске оркестратора") from e