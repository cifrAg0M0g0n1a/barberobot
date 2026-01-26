import logging
from contextlib import asynccontextmanager
import sys
from pathlib import Path


if str(Path(__file__).parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from database.database import create_tables, seed_services
from database.backup import backup_db
from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.staticfiles import StaticFiles
from routes import router
from backend.utils.logger import get_logger
from backend.helpers.log_cleanup_task import start_log_cleanup
from backend.helpers.backup_task import start_backup_task
from aiogram import Bot
from config import BOT_TOKEN
from helpers.reminder import scheduler, schedule_reminders


logger = get_logger(__name__)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")


logger.info("Backend logger initialized")

bot = Bot(token=BOT_TOKEN)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: backup and initialize DB")

    backup_db()
    create_tables()
    seed_services()

    bot = Bot(token=BOT_TOKEN)
    scheduler.start()
    await schedule_reminders(bot)

    start_log_cleanup(bot)
    start_backup_task()

    yield
    logger.info("Shutdown")
    scheduler.shutdown(wait=False)
    await bot.session.close()


app = FastAPI(
    title="TimeToCut API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

templates_dir = Path(__file__).parent / "templates"
app.mount("/static", StaticFiles(directory=str(templates_dir)), name="static")

if __name__ == "__main__":
    logger.info("Starting backend server via uvicorn")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
