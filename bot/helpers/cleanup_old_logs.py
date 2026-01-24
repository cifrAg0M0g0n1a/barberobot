import os
import glob
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Bot
import logging

from aiogram.types import FSInputFile

from config import DEVELOPER_ID
from settings import RETENTION_DAYS

logger = logging.getLogger(__name__)

developer_id = DEVELOPER_ID
LOG_DIR = Path(__file__).parent.parent
LOG_PATTERN = str(LOG_DIR / "bot.log.*")
retention_days = RETENTION_DAYS


async def send_and_cleanup_old_logs(bot: Bot):
    """Отправка старых логов в Telegram и удаление файлов старше retention_days"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    log_files = glob.glob(str(LOG_PATTERN))

    for log_file in log_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
        if mtime < cutoff:
            zip_name = f"{log_file}.zip"
            try:
                with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(log_file, arcname=os.path.basename(log_file))

                with open(zip_name, "rb") as f:
                    log_path = Path(log_file)

                    await bot.send_document(
                        chat_id=developer_id,
                        document=FSInputFile(path=zip_name),
                        caption=f"🧾 Bot log\n({log_path.name})",
                    )

                os.remove(log_file)
                os.remove(zip_name)

                logger.info(f"Лог {log_file} отправлен и удалён")
            except Exception as e:
                logger.error(f"Ошибка при отправке логов {log_file}: {e}")
