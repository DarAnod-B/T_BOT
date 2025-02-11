import logging
from datetime import datetime

def setup_logger() -> logging.Logger:
    # Настройка имени файла логов
    log_filename = f"logs/bot_{datetime.now().strftime('%Y%m%d_%H-%M-%S')}.log"
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s")

    # Создание файлового обработчика
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Создание обработчика для вывода в консоль
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Проверка, чтобы избежать дублирования обработчиков
    if not root_logger.hasHandlers():
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

    return logging.getLogger(__name__)