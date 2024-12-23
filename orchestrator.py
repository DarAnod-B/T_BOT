import docker
import os
import time
import traceback
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = docker.from_env()

# Получаем абсолютный путь к директории data
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

def run_container(image_name, environment=None, command=None, retries=3, delay=5):
    """
    Запуск контейнера с динамической передачей параметров с обработкой ошибок и повторным запуском.

    :param image_name: Имя образа контейнера.
    :param environment: Переменные окружения для контейнера.
    :param command: Команда для выполнения в контейнере.
    :param retries: Количество попыток в случае ошибки.
    :param delay: Задержка в секундах между повторными попытками.
    :return: Логи контейнера.
    """
    attempt = 0  # Счетчик попыток запуска
    while attempt < retries:
        try:
            container = client.containers.run(
                image_name,
                detach=True,
                volumes={
                    data_path: {
                        "bind": "/app/data",
                        "mode": "rw",
                    },  # Монтируем локальную директорию
                },
                environment=environment if environment else {},
                command=command,
            )
            logging.info(f"Запущен контейнер {image_name}, id: {container.short_id}")

            # Ждем завершения контейнера
            result = container.wait()
            exit_code = result['StatusCode']

            if exit_code != 0:
                raise RuntimeError(f"Контейнер {image_name} завершился с ошибкой (код {exit_code})")

            logs = container.logs().decode("utf-8")
            logging.info(f"Контейнер {image_name} завершён успешно")

            container.remove()
            return logs

        except Exception as e:
            attempt += 1
            logging.error(f"Ошибка при запуске контейнера {image_name}: {e}")
            logging.error(f"Попытка {attempt} из {retries}")
            traceback.print_exc()

            if attempt >= retries:
                logging.error(f"Не удалось запустить контейнер {image_name} после {retries} попыток.")
                raise e

            time.sleep(delay)