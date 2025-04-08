# app/models/request.py
from pydantic import BaseModel, FilePath, DirectoryPath
from typing import Optional, Union

class DocumentRequest(BaseModel):
    """Request model for document summarization."""
    file_path: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/path/to/document.pdf"
            }
        }

class FolderRequest(BaseModel):
    """Request model for folder summarization."""
    folder_path: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "folder_path": "/path/to/documents/folder"
            }
        }