import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List # Import List for type hinting

class Settings(BaseSettings):
    APP_NAME: str = "Summarize documetn API"
    API_V1_STR: str = "/api"

    # Temporary file directory
    # Use Path for better path manipulation
    TEMP_DIR: Path = Path("temp_files")

    # Whisper settings
    WHISPER_MODEL: str = 'base'

    # Ollama settings
    OLLAMA_API_URL: str = 'http://localhost:11434/api/generate'
    OLLAMA_MODEL: str = 'llama3.2:1b' # Or your preferred default
    OLLAMA_TIMEOUT: float = 300.0 # Timeout in seconds

    # Chunking settings
    MAX_LENGTH_PER_CHUNK: int = 20000
    MAX_TOKEN_PER_CHUNK_GROUPED: int = 2048
    OVERLAPP_CHUNK: int = 500

    GEMINI_API_KEY:str="AIzaSyBSrT4FjRJB9l7Itgk1DqyJeyQ3Gm4eNNE"
    GEMINI_MODEL_NAME:str="gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL:str="models/text-embedding-004"


    NOUGAT_URL:str='http://127.0.0.1:8503/predict/'
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
    MONGODB_SUMMARY_COLLECTION: str = "summary"

    CHUNCKER_TYPE: str="cosine" #standard or cosine
    TEST_PHASE: bool= False
    
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
