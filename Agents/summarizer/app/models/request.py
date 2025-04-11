# app/models/request.py
from pydantic import Field
from pydantic import BaseModel, FilePath, DirectoryPath
from typing import Optional, Union
from enum import Enum
class SummaryType(str, Enum):
    """Enum for summarization types."""
    STANDARD = "standard"
    TECHNICAL = "technical"
    KEY_POINTS = "key_points"
    LAYMAN = "simple"

class DocumentRequest(BaseModel):
    """Request model for document summarization."""
    file_name: str = Field(..., description="Name of the document to to summarize")
    summary_type: SummaryType=Field(..., description="Type of summary to generate (standard, technical, key_points, simple)")