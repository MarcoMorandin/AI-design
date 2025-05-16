import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Summarize Document API"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Chunking settings
    MAX_LENGTH_PER_CHUNK: int = int(os.getenv("MAX_LENGTH_PER_CHUNK", "30000"))
    MAX_TOKEN_PER_CHUNK_GROUPED: int = int(
        os.getenv("MAX_TOKEN_PER_CHUNK_GROUPED", "2048")
    )
    OVERLAPP_CHUNK: int = int(os.getenv("OVERLAPP_CHUNK", "500"))

    # API Keys (securely loaded from environment variables)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
    GEMINI_EMBEDDING_MODEL: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"
    )

    # Other API keys
    GOOGLE_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Logging and monitoring
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "False").lower() == "true"

    # Security and timeout settings
    MAX_DOWNLOAD_SIZE_MB: int = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "200"))
    DOWNLOAD_TIMEOUT: float = float(os.getenv("DOWNLOAD_TIMEOUT", "120.0"))

    # File processing settings
    ALLOWED_DOCUMENT_CONTENT_TYPES: List[str] = [
        "pdf",
        "docx",
        "doc",
        "ppt",
        "pptx",
        "md",
    ]

    # Chunker configuration
    CHUNCKER_TYPE: str = os.getenv("CHUNCKER_TYPE", "cosine")  # standard or cosine
    TEST_PHASE: bool = os.getenv("TEST_PHASE", "False").lower() == "true"

    # ML model configurations
    IMAGE_DESCRIPTION_EXTRACTION_MODEL: str = os.getenv(
        "IMAGE_DESCRIPTION_MODEL", "Salesforce/blip-image-captioning-large"
    )

    # Temporary directory for file processing
    TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "/tmp/chunker"))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create a single settings instance to be imported
settings = Settings()

# Set up logging based on config
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
logging.getLogger().setLevel(log_level)

# Log startup configuration (but hide sensitive values)
if settings.ENVIRONMENT != "production":
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} environment")
    logger.info(
        f"Chunking settings: MAX_LENGTH={settings.MAX_LENGTH_PER_CHUNK}, "
        f"MAX_TOKEN={settings.MAX_TOKEN_PER_CHUNK_GROUPED}, "
        f"OVERLAP={settings.OVERLAPP_CHUNK}"
    )
    logger.info(f"Using chunker type: {settings.CHUNCKER_TYPE}")

# Ensure temp directory exists
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
