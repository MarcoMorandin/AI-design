# app/models/request.py
import uuid
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

class TaskRequest(BaseModel):
    """Request model for testing document extraction."""
    file_path: Union[FilePath, DirectoryPath] = Field(..., description="Path to the document to extract")

class TextExtractionResponseSummaryRequest(BaseModel):
    """Request model for document summarization."""
    task_id: uuid.UUID = Field(..., description="Name of the document to to summarize")
    summary_type: SummaryType=Field(..., description="Type of summary to generate (standard, technical, key_points, simple)")