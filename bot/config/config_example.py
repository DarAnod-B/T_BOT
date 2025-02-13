import os

# Токен бота
BOT_TOKEN = os.getenv(
    "BOT_TOKEN", "..."
)


MEMORY_LIMIT = 4 * 1024 * 1024 * 1024  # 4GB в байтах
SWAP_LIMIT = 4 * 1024 * 1024 * 1024  # 4GB Swap