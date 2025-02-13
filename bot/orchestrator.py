import aiodocker
import asyncio
import os
import logging
from contextlib import asynccontextmanager
from bot.config.config import *
# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Путь к данным
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

class Orchestrator:
    def __init__(self):
        self.docker = None
        self.active_containers = set()

    async def initialize(self):
        """Асинхронная инициализация Docker клиента"""
        try:
            self.docker = aiodocker.Docker()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.critical(f"Failed to initialize Docker client: {e}")
            raise

    @asynccontextmanager
    async def managed_container(self, container):
        """Контекстный менеджер для управления контейнером"""
        self.active_containers.add(container.id)
        try:
            yield container
        finally:
            await self.cleanup_container(container.id)

    async def cleanup_container(self, container_id):
        """Удаление контейнера с проверкой его существования"""
        if container_id in self.active_containers:
            try:
                container = await self.docker.containers.get(container_id)
                await container.delete(force=True)
                logger.info(f"Container {container_id[:12]} removed")
            except aiodocker.exceptions.DockerError as e:
                logger.error(f"Failed to remove container {container_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error while removing container {container_id}: {e}")
            finally:
                self.active_containers.discard(container_id)

    async def stream_logs(self, container):
        """Стриминг логов контейнера"""
        container_id = container.id[:12]
        try:
            logger.info(f"Starting log stream for {container_id}")
            async for line in container.log(stdout=True, stderr=True, follow=True):
                log_line = line.decode("utf-8", errors="replace").strip() if isinstance(line, bytes) else line.strip()
                logger.info(f"[{container_id}] {log_line}")
        except asyncio.CancelledError:
            logger.warning(f"Log stream task was cancelled for {container_id}")
        except Exception as e:
            logger.error(f"Log stream error for {container_id}: {e}")
        finally:
            logger.info(f"Log stream ended for {container_id}")

    async def run_container(
        self,
        image_name: str,
        environment: dict = None,
        command: str = None,
        retries: int = 3,
        delay: int = 10,
        ports: dict = None
    ):
        """Запуск контейнера с ограничением памяти"""
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{retries} to run {image_name}")

                # Ограничение памяти (4GB RAM + 4GB Swap)
                

                # Проверяем, есть ли порты
                port_bindings = {}
                exposed_ports = {}
                if ports:
                    for c_port, h_port in ports.items():
                        port_bindings[f"{c_port}/tcp"] = [{"HostPort": str(h_port)}]
                        exposed_ports[f"{c_port}/tcp"] = {}

                config = {
                    "Image": image_name,
                    "Env": [f"{k}={v}" for k, v in (environment or {}).items()],
                    "HostConfig": {
                        "Binds": [f"{data_path}:/app/data:rw"],
                        "PortBindings": port_bindings,
                        "Memory": MEMORY_LIMIT,  # Ограничение RAM (4GB)
                        "MemorySwap": SWAP_LIMIT,  # Swap (4GB)
                    },
                    "ExposedPorts": exposed_ports
                }

                if command:
                    config["Cmd"] = command.split()

                container = await self.docker.containers.create(config)
                async with self.managed_container(container):
                    await container.start()
                    log_task = asyncio.create_task(self.stream_logs(container))

                    try:
                        result = await asyncio.wait_for(container.wait(), timeout=300)
                        logs = await container.log(stdout=True, stderr=True)
                        decoded_logs = "".join(
                            line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
                            for line in logs
                        )
                        return decoded_logs, result["StatusCode"]
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout while waiting for {image_name}")
                        await self.cleanup_container(container.id)
                    finally:
                        await asyncio.sleep(1)
                        await log_task

            except aiodocker.exceptions.DockerError as e:
                logger.error(f"Container error: {e}, attempt {attempt}/{retries}")
            except Exception as e:
                logger.critical(f"Unexpected error while running {image_name}: {e}")

            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

        raise RuntimeError(f"Failed to start container {image_name} after {retries} attempts")

    async def shutdown(self):
        """Завершение работы: удаление контейнеров и закрытие клиента"""
        logger.info("Cleaning up all containers...")
        await asyncio.gather(*(self.cleanup_container(cid) for cid in list(self.active_containers)))
        if self.docker:
            await self.docker.close()
            logger.info("Docker client closed")

# Создание глобального экземпляра
orchestrator = Orchestrator()