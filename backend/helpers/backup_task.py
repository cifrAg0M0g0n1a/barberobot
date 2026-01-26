import asyncio
from aiogram import Bot
from database.backup import backup_db, send_backup_to_telegram
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_backup_task = None
_backup_bot = None


def start_backup_task(bot: Bot):
    """Запускает фоновую задачу для создания бэкапов БД каждые 6 часов"""
    global _backup_task, _backup_bot

    if _backup_task:
        return

    _backup_bot = bot

    async def loop():
        while True:
            try:
                backup_path, timestamp = backup_db()
                await send_backup_to_telegram(_backup_bot, backup_path, timestamp)
                logger.info("Автоматический бэкап БД успешно создан и отправлен")
            except Exception as e:
                logger.error(f"Ошибка при создании автоматического бэкапа БД: {e}")
            await asyncio.sleep(6 * 60 * 60)

    _backup_task = asyncio.create_task(loop())
