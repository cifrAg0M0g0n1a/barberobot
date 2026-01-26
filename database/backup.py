import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import DEVELOPER_ID
from database.database import DB_PATH

BACKUP_DIR = Path(DB_PATH).parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


def backup_db(bot: Optional[object] = None):
    """
    Создает бэкап базы данных
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_path = BACKUP_DIR / f"db_{timestamp}.sqlite3"

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(backup_path)

    src.backup(dst)

    src.close()
    dst.close()

    return backup_path, timestamp


async def send_backup_to_telegram(bot, backup_path: Path, timestamp: str):
    """
    Отправляет файл бэкапа в Telegram
    """
    try:
        from aiogram.types import FSInputFile

        file = FSInputFile(str(backup_path))
        await bot.send_document(
            chat_id=DEVELOPER_ID,
            document=file,
            caption=f"📦 Бэкап базы данных\n🕒 {timestamp}",
        )
    except Exception as e:
        print(f"Ошибка при отправке бэкапа в Telegram: {e}")
