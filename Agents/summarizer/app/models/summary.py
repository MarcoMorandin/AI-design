# app/models/task.py
import uuid
import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.request import SummaryType

class SummaryStatus(str, Enum):
    """Enum for task processing status."""
    PENDING="PENDING"
    GETTING_TEXT="GETTING_TEXT"
    CHUNKING = "CHUNKING"
    SUMMARIZING = "SUMMARIZING"
    DONE = "DONE"
    FAILED = "FAILED"



class SummaryDocument(BaseModel):
    """Database model for a document summarization task."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id") # Use UUID, map to _id
    summary_id: uuid.UUID = Field(..., description="Public facing task identifier") # Redundant but useful for query
    #file_name: str
    status: SummaryStatus = SummaryStatus.PENDING
    summary_type: SummaryType = SummaryType.STANDARD # Store the requested type
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    error_message: Optional[str] = None
    summary: Optional[str] = None

    
    class Config:
        populate_by_name = True # allow alias
        json_encoders = {
            uuid.UUID: str,
            datetime.datetime: lambda v: v.isoformat()
        }

class SummaryCreationResponse(BaseModel):
    """API response model for task creation."""
    summary_id: uuid.UUID

class SummaryStatusResponse(BaseModel):
    """API response model for task status."""
    summary_id: uuid.UUID
    status: SummaryStatus
    updated_at: datetime.datetime

class SummaryResultResponse(BaseModel):
    """API response model for task result."""
    summary_id: uuid.UUID
    status: SummaryStatus
    file_name: str
    summary_type: SummaryType
    summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime