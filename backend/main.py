import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.staticfiles import StaticFiles
from routes import router

app = FastAPI(title="TimeToCut API")

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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
