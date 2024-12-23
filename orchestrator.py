import docker
import os
import time
import traceback
import logging


def stream_logs(container):
    """
    Поток для стриминга логов контейнера.
    """
    logging.info(f"Подписка на логи контейнера {container.short_id}...")
    try:
        for log in container.logs(stream=True, follow=True):
            logging.info(f"[{container.short_id}] {log.decode('utf-8').strip()}")
    except Exception as e:
        logging.error(f"Ошибка при чтении логов контейнера {container.short_id}: {e}")


try:
    client = docker.from_env()
    logging.info("Успешно подключились к Docker")
except docker.errors.DockerException as e:
    logging.critical(f"Ошибка при подключении к Docker, проверьте, запущен ли Docker: {e}")
    exit(1)
# Получаем абсолютный путь к директории data
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

def run_container(image_name, environment=None, command=None, retries=3, delay=20):
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
            logging.info(f"Попытка {attempt + 1} из {retries} запуска контейнера {image_name}")


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

            # Стримим логи контейнера
            stream_logs(container)
            
            # Ждем завершения контейнера
            result = container.wait()
            exit_code = result['StatusCode']

            if exit_code != 0:
                logging.error(f"Контейнер {image_name} завершился с ошибкой. Код выхода: {exit_code}")
            else:
                logging.info(f"Контейнер {image_name} завершился успешно.")

            logs = container.logs().decode("utf-8")
            # logging.info(f"Все логи контейнера:\n{logs}")

            # Удаляем контейнер
            try:
                if client.containers.get(container.id):
                    container.remove()
            except docker.errors.NotFound:
                pass

            logging.info(f"Контейнер {container.short_id} удалён.")
            return logs

        except Exception as e:
            attempt += 1
            logging.error(f"Ошибка при запуске контейнера {image_name}: {e}", exc_info=True)
            logging.error(f"Попытка {attempt} из {retries}")
            traceback.print_exc()

            if attempt >= retries:
                logging.critical(f"Не удалось запустить контейнер {image_name} после {retries} попыток.")
                raise e

            time.sleep(delay)