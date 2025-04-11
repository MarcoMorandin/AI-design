# app/models/task.py
import uuid
import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    """Enum for task processing status."""
    DOWNLOADING="DOWNLOADING"
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING_TEXT"
    SUMMARIZING = "GENERATING_SUMMARY"
    DONE = "DONE"
    FAILED = "FAILED"

class TaskDocument(BaseModel):
    """Database model for a document summarization task."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id") # Use UUID, map to _id
    task_id: uuid.UUID = Field(..., description="Public facing task identifier") # Redundant but useful for query
    file_name: str
    status: TaskStatus = TaskStatus.PENDING
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

class TaskCreationResponse(BaseModel):
    """API response model for task creation."""
    task_id: uuid.UUID

class TaskStatusResponse(BaseModel):
    """API response model for task status."""
    task_id: uuid.UUID
    status: TaskStatus
    updated_at: datetime.datetime

class TaskResultResponse(BaseModel):
    """API response model for task result."""
    task_id: uuid.UUID
    status: TaskStatus
    file_name: str
    summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime