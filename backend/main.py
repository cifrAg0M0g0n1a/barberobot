import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
import sys
from pathlib import Path


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


logger = get_logger(__name__)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")


logger.info("Backend logger initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: backup and initialize DB")
    backup_db()
    create_tables()
    seed_services()
    yield
    logger.info("Shutdown")


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
