import asyncio
import logging
from logging.handlers import RotatingFileHandler
from bot.bot import setup_bot

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


async def main():
    bot, dp = setup_bot()
    botName = await bot.get_me()
    logger.info(f"Start bot: {botName.username}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
