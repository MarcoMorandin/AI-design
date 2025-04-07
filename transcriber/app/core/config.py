import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List # Import List for type hinting

class Settings(BaseSettings):
    APP_NAME: str = "Video to Essay API"
    API_V1_STR: str = "/api"

    # Temporary file directory
    # Use Path for better path manipulation
    TEMP_DIR: Path = Path("temp_files")

    # Whisper settings
    WHISPER_MODEL: str = 'base'

    # Ollama settings
    OLLAMA_API_URL: str = 'http://localhost:11434/api/generate'
    OLLAMA_MODEL: str = 'llama3.2:3b' # Or your preferred default
    OLLAMA_TIMEOUT: float = 300.0 # Timeout in seconds

    # Chunking settings
    MAX_CHARS_PER_CHUNK: int = 4000
    CHUNK_OVERLAP_CHARS: int = 500

    # Logging Level (e.g., INFO, DEBUG, WARNING)
    LOG_LEVEL: str = "INFO"

    MAX_DOWNLOAD_SIZE_MB: int = 200 # Limit in Megabytes
    DOWNLOAD_TIMEOUT: float = 120.0 # Timeout for download connection/read

    # Define allowed content types (lowercase) - check starts of MIME types
    ALLOWED_VIDEO_CONTENT_TYPES: List[str] = [
        "video/mp4",
        "video/webm",
        "video/quicktime", # .mov
        "video/x-matroska", # .mkv
        "video/avi",
        "video/mpeg",
        "video/x-ms-wmv", # .wmv
        "video/x-flv", # .flv
    ]
    
    MONGODB_URL: str = "mongodb+srv://test:test@ai-design.nld514j.mongodb.net/"
    MONGODB_DB_NAME: str = "test"
    MONGODB_TASK_COLLECTION: str = "tasks"
    
    class Config:
        # Reads variables from a .env file if present
        env_file = ".env"
        env_file_encoding = 'utf-8'
        # Makes TEMP_DIR relative to the project root if not absolute
        # This assumes you e project root dirrun the app from thectory
        # Adjust if needed based on your execution context
        # TEMP_DIR = Path(__file__).parent.parent.parent / "temp_files"


# Create a single settings instance to be imported
settings = Settings()

# Ensure temp directory exists
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)