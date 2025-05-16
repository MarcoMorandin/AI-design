import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List  # Import List for type hinting


class Settings(BaseSettings):
    APP_NAME: str = "Summarize document API"
    API_V1_STR: str = "/api"

    # Chunking settings
    MAX_LENGTH_PER_CHUNK: int = 30000
    MAX_TOKEN_PER_CHUNK_GROUPED: int = 256
    OVERLAPP_CHUNK: int = 100
    MAX_LENGTH_PER_CHUNK_GROUPED_COSINE: int = 1024

    GEMINI_API_KEY: str = "AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE"
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    MONGO_URI: str = ""
    MONGO_DB_NAME: str = ""
    # Add these fields to match your environment variables
    google_api_key: str = ""
    groq_api_key: str = ""

    # Add these lines:
    qdrant_api_key: str = ""
    qdrant_host: str = ""

    # Logging Level (e.g., INFO, DEBUG, WARNING)
    LOG_LEVEL: str = "INFO"

    MAX_DOWNLOAD_SIZE_MB: int = 200  # Limit in Megabytes
    DOWNLOAD_TIMEOUT: float = 120.0  # Timeout for download connection/read

    # Define allowed content types (lowercase) - check starts of MIME types
    ALLOWED_DOCUMENT_CONTENT_TYPES: List[str] = [
        "pdf",
        "docx",
        "doc",
        "ppt",
        "pptx",
        "md",
    ]

    CHUNCKER_TYPE: str = "cosine"  # standard or cosine
    TEST_PHASE: bool = False

    IMAGE_DESCRIPTION_EXTRACTION_MODEL: str = "Salesforce/blip-image-captioning-large"

    environment: str = "production"  # Or "development", provide a sensible default
    enable_metrics: bool = False  # Or False, provide a sensible default
    temp_dir: Path = Path("temp_files")  # Define a default path

    class Config:
        # Reads variables from a .env file if present
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Makes TEMP_DIR relative to the project root if not absolute
        # This assumes you e project root dirrun the app from thectory
        # Adjust if needed based on your execution context
        # TEMP_DIR = Path(__file__).parent.parent.parent / "temp_files"

        # Alternatively, you can allow extra fields with this setting:
        # extra = "allow"


# Create a single settings instance to be imported
settings = Settings()

# Ensure temp directory exists
# settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
