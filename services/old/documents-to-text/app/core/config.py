from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Document text extractor API"
    API_V1_STR: str = "/api"

    TEMP_DIR: Path = Path("temp_files")

    NOUGAT_URL:str='http://nougat.iliadboxos.it:25000'
    NOUGAT_API_KEY:str = '81ede5b5-ff0a-436e-89b1-ed331ea98444'
    
    # Logging Level (e.g., INFO, DEBUG, WARNING)
    LOG_LEVEL: str = "INFO"

    MAX_DOWNLOAD_SIZE_MB: int = 200 # Limit in Megabytes
    DOWNLOAD_TIMEOUT: float = 120.0 # Timeout for download connection/read

    # Define allowed content types (lowercase) - check starts of MIME types
    ALLOWED_DOCUMENT_CONTENT_TYPES: List[str] = [
        "pdf",
        "docx",
        "doc",
        "ppt",
        "pptx",
        "md"
    ]
    
    MONGODB_URL: str = "mongodb+srv://test:test@ai-designing.psxhnz0.mongodb.net/"
    MONGODB_DB_NAME: str = "test"
    MONGODB_TASK_COLLECTION: str = "tasks"
    IMAGE_DESCRIPTION_EXTRACTION_MODEL: str = "Salesforce/blip-image-captioning-large"
    
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
