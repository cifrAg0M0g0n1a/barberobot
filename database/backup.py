import sqlite3
from pathlib import Path
from datetime import datetime

from database.database import DB_PATH

BACKUP_DIR = Path(DB_PATH).parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


def backup_db():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_path = BACKUP_DIR / f"db_{timestamp}.sqlite3"

    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(backup_path)

    src.backup(dst)

    src.close()
    dst.close()
