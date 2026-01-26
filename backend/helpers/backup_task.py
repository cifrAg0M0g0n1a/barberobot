import asyncio
from database.backup import backup_db
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_backup_task = None


def start_backup_task():
    """Запускает фоновую задачу для создания бэкапов БД каждые 6 часов"""
    global _backup_task

    if _backup_task:
        return

    async def loop():
        while True:
            try:
                backup_db()
                logger.info("Автоматический бэкап БД успешно создан")
            except Exception as e:
                logger.error(f"Ошибка при создании автоматического бэкапа БД: {e}")
            await asyncio.sleep(6 * 60 * 60)

    _backup_task = asyncio.create_task(loop())
