# app/models/task.py
import uuid
import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    """Enum for task processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    SUMMARIZING = "summarizing"
    DONE = "done"
    FAILED = "failed"

class TaskDocument(BaseModel):
    """Database model for a document summarization task."""
    task_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    file_path: str
    status: TaskStatus = TaskStatus.PENDING
    error_message: Optional[str] = None
    summary: Optional[str] = None
    summary_path: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    class Config:
        populate_by_name = True
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
    file_path: str
    summary: Optional[str] = None
    summary_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime