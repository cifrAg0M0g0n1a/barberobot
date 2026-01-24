import asyncio
from aiogram import Bot
from helpers.cleanup_old_logs import send_and_cleanup_old_logs
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_cleanup_task = None


def start_log_cleanup(bot: Bot):
    global _cleanup_task

    if _cleanup_task:
        return

    async def loop():
        while True:
            try:
                await send_and_cleanup_old_logs(bot)
            except Exception as e:
                logger.error(f"Ошибка cleanup backend логов: {e}")
            await asyncio.sleep(24 * 60 * 60)  # раз в сутки

    _cleanup_task = asyncio.create_task(loop())
