import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import FSInputFile
from config import OWNER_ID
from settings import RETENTION_DAYS
from backend.utils.logger import get_logger

logger = get_logger(__name__)

LOG_DIR = Path(__file__).parent.parent
LOG_PREFIX = "backend.log"
retention_days = RETENTION_DAYS


async def send_and_cleanup_old_logs(bot: Bot):
    now = datetime.now()
    cutoff = now - timedelta(days=retention_days)

    for log_file in LOG_DIR.glob(f"{LOG_PREFIX}*"):
        if log_file.name == LOG_PREFIX:
            continue

        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime > cutoff:
                continue

            zip_path = log_file.with_suffix(log_file.suffix + ".zip")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(log_file, arcname=log_file.name)

            await bot.send_document(
                OWNER_ID,
                FSInputFile(zip_path),
                caption=f"🧾 Backend log ({log_file.name})",
            )

            log_file.unlink(missing_ok=True)
            zip_path.unlink(missing_ok=True)

            logger.info(f"Отправлен и удалён лог: {log_file.name}")

        except Exception as e:
            logger.error(f"Ошибка при обработке {log_file}: {e}")
