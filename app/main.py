import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.csv_routes import router as csv_router
from app.api.schema_routes import router as schema_router
from app.api.upload_routes import router as upload_router

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

APP_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(APP_DIR, "static")

app = FastAPI(title="CSV to SQL Server Uploader", version="0.1.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.include_router(csv_router, prefix="/api")
app.include_router(schema_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
