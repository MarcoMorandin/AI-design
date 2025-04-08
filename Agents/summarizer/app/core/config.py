# app/core/config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Document Summarization API"
    
    # MongoDB Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "summarizer_db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")
    
    # Google Gemini API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    
    # File Storage
    TEMP_FILES_DIR: str = os.getenv("TEMP_FILES_DIR", "temp_files")
    SUMMARY_RESULTS_DIR: str = os.getenv("SUMMARY_RESULTS_DIR", "summary_results")
    
    # Processing Configuration
    MAX_CHUNK_TOKENS: int = int(os.getenv("MAX_CHUNK_TOKENS", "4000"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "5"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()