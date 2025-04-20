# app/models/task.py
import uuid
import datetime
from enum import Enum
from typing import Optional
from venv import create
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    """Enum for task processing status."""
    PENDING="PENDING"
    GETTING_TEXT="GETTING_TEXT"
    UPLOADING = "UPLOADING"
    DONE = "DONE"
    FAILED = "FAILED"

class TaskDocument(BaseModel):
    """Database model for a document summarization task."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id") # Use UUID, map to _id
    task_id: uuid.UUID = Field(..., description="Public facing task identifier") # Redundant but useful for query
    summary_id: uuid.UUID = Field(..., description="Private identifier for summary")
    status: TaskStatus = TaskStatus.PENDING
    created_document_id: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    error_message: Optional[str] = None

    
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
    error: Optional[str] = None
    created_document_id: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime