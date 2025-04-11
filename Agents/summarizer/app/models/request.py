# app/models/request.py
from pydantic import Field
from pydantic import BaseModel, FilePath, DirectoryPath
from typing import Optional, Union

class DocumentRequest(BaseModel):
    """Request model for document summarization."""
    file_name: str = Field(..., description="Name of the document to to summarize")