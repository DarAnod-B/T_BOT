import aiodocker
import asyncio
import os
import logging
from contextlib import asynccontextmanager

# Используем модульный логгер
logger = logging.getLogger(__name__)
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

class Orchestrator:
    def __init__(self):
        self.docker = None
        self.active_containers = set()

    async def initialize(self):
        """Асинхронная инициализация Docker клиента"""
        self.docker = aiodocker.Docker()
        logger.info("Docker client initialized")

    @asynccontextmanager
    async def managed_container(self, container):
        self.active_containers.add(container.id)
        try:
            yield container
        finally:
            await self.cleanup_container(container.id)

    async def cleanup_container(self, container_id):
        try:
            container = await self.docker.containers.get(container_id)
            await container.delete(force=True)
            self.active_containers.discard(container_id)
            logger.info(f"Container {container_id[:12]} cleaned up")
        except aiodocker.exceptions.DockerError as e:
            logger.error(f"Error cleaning up container {container_id}: {e}")

    async def stream_logs(self, container):
        container_id = container.id[:12]
        try:
            logger.info(f"Starting log stream for {container_id}")
            async for line in container.log(stdout=True, stderr=True, follow=True):
                try:
                    log_line = line.decode("utf-8", errors="replace").strip() if isinstance(line, bytes) else line.strip()
                    logger.info(f"[{container_id}] {log_line}")
                except Exception as e:
                    logger.error(f"Log processing error: {e}")
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
        delay: int = 20
    ):
        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{retries} to run {image_name}")

                config = {
                    "Image": image_name,
                    "Env": [f"{k}={v}" for k, v in (environment or {}).items()],
                    "HostConfig": {"Binds": [f"{data_path}:/app/data:rw"]}
                }
                if command:
                    config["Cmd"] = command.split()

                container = await self.docker.containers.create(config)
                async with self.managed_container(container):
                    await container.start()
                    log_task = asyncio.create_task(self.stream_logs(container))
                    
                    try:
                        result = await container.wait()
                        logs = await container.log(stdout=True, stderr=True)
                        decoded_logs = "".join([
                            line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line
                            for line in logs
                        ])
                        return decoded_logs, result["StatusCode"]
                    finally:
                        await log_task  # Ждем завершения задачи логирования
                        
            except aiodocker.exceptions.DockerError as e:
                logger.error(f"Container error: {e}, attempt {attempt}/{retries}")
                if attempt == retries:
                    raise
                await asyncio.sleep(delay)

    async def shutdown(self):
        logger.info("Cleaning up all containers...")
        await asyncio.gather(*(self.cleanup_container(cid) for cid in self.active_containers))
        if self.docker:
            await self.docker.close()
            logger.info("Docker client closed")

orchestrator = Orchestrator()