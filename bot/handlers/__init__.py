from .start_handler import router as start_router
from .presentation_create_handler import router as links_router
from .logs_handler import router as logs_router
from .cancel_handler import router as cancel_router

routers = [
    start_router,
    links_router,
    logs_router,
    cancel_router
]