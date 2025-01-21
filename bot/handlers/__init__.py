from aiogram import Router
import logging

# Создаем общий логгер для модуля handlers
logger = logging.getLogger("handlers")  # Можно задать имя логгера для логов из всех обработчиков


from .cancel_handler import cancel_router
from .links_to_presentations_handler import links_to_presentations_router 
from .log_handler import log_router
from .start_handler import start_router


# Создаем общий роутер
router = Router()

# Включаем все локальные роутеры в общий
router.include_router(start_router)
router.include_router(cancel_router)
router.include_router(log_router)
router.include_router(links_to_presentations_router )

logger.info("Все обработчики успешно добавлены в роутер")
