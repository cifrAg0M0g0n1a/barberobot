import sys
from pathlib import Path

if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot
from bot.bot import setup_bot
from helpers.cleanup_old_logs import send_and_cleanup_old_logs


logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Вывод в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Вывод в файл (rotating: max 5MB, 3 файла)
file_handler = RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


async def log_cleanup_loop(bot: Bot):
    """Фоновая задача для отправки и удаления старых логов раз в день"""
    while True:
        try:
            await send_and_cleanup_old_logs(bot)
        except Exception as e:
            logger.error(f"Ошибка в фоновом таске очистки логов: {e}")
        await asyncio.sleep(24 * 60 * 60)


async def main():
    bot, dp = setup_bot()

    asyncio.create_task(log_cleanup_loop(bot))

    botName = await bot.get_me()
    logger.info(f"Start bot: {botName.username}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
