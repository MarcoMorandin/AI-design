# app/main.py
import logging.config
from fastapi import FastAPI

from app.api.endpoints import tasks as tasks_router # Import new tasks router
from app.core.config import settings
from app.db.mongodb import connect_to_mongo, close_mongo_connection # Import DB functions
from app.core.config import settings

# Configure logging
# You could put this dict in a separate logging_config.py
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
            "level": settings.LOG_LEVEL.upper(), # Use level from settings
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["console"], # Add "file" here if using file handler
            "level": "WARNING", # Set root level higher to avoid library spam
            "propagate": False,
        },
        "app": { # Logger for your application module
            "handlers": ["console"], # Add "file" here if needed
            "level": settings.LOG_LEVEL.upper(),
            "propagate": False, # Don't propagate to root if handled here
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
         # Adjust levels for libraries if needed (e.g., httpx, moviepy)
         "httpx": {
             "handlers": ["console"],
             "level": "WARNING",
             "propagate": False,
         },
          "moviepy": {
             "handlers": ["console"],
             "level": "WARNING", # Moviepy can be verbose
             "propagate": False,
         }
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app.main") # Get logger for this module

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" # Place OpenAPI spec under version
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Video to Essay API...")
    await connect_to_mongo() # Connect to DB on startup
    logger.info(f"Temporary file directory: {settings.TEMP_DIR.resolve()}")
    # Add any other startup logic here (e.g., check Ollama connection)
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down API...")
    await close_mongo_connection() # Disconnect from DB on shutdown
    
app.include_router(tasks_router.router, prefix=settings.API_V1_STR + "/tasks", tags=["Tasks"])

@app.get("/")
async def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /docs for API documentation."}

# --- Uvicorn runner (for direct execution, e.g., python app/main.py) ---
# Usually you run with `uvicorn app.main:app --reload` from the project root
if __name__ == "__main__":
    import uvicorn
    logger.info("Running Uvicorn directly from main.py (for development only)...")
    uvicorn.run(
        "app.main:app", # Point to the app object
        host="0.0.0.0",
        port=8000,
        reload=True, # Enable reload for development
        log_config=LOGGING_CONFIG # Pass logging config to uvicorn
        )