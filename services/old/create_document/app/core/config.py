from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "Upload documents"
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

    UPLOAD_DOCUMENTS_URL:str='http://localhost:3000/api/documents/uploadMarkdown'

    NOUGAT_URL:str='http://127.0.0.1:8503/predict/'
    # Logging Level (e.g., INFO, DEBUG, WARNING)
    LOG_LEVEL: str = "INFO"

    MAX_DOWNLOAD_SIZE_MB: int = 200 # Limit in Megabytes
    DOWNLOAD_TIMEOUT: float = 120.0 # Timeout for download connection/read

        
    MONGODB_URL: str = "mongodb+srv://test:test@ai-designing.psxhnz0.mongodb.net/"
    MONGODB_DB_NAME: str = "test"
    MONGODB_SUMMARY_COLLECTION: str = "summary"
    MONGODB_UPLOAD_COLLECTION: str = "uploads"

    CHUNCKER_TYPE: str="cosine" #standard or cosine
    TEST_PHASE: bool= False
    
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
