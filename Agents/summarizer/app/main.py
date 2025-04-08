# app/main.py
import logging.config
from fastapi import FastAPI

from app.api.endpoints import tasks as tasks_router
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection

# Configure logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": settings.LOG_LEVEL.upper(),
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "app": {
            "handlers": ["console"],
            "level": settings.LOG_LEVEL.upper(),
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")

app = FastAPI(title="Document Summarization API", description="API for summarizing documents using AI")

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    logger.info("Connected to MongoDB")

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")

# Include routers
app.include_router(tasks_router.router, prefix="/api/tasks", tags=["tasks"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Document Summarization API"}