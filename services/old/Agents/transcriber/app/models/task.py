# app/models/task.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum
import datetime
import uuid

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    EXTRACTING = "EXTRACTING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    GENERATING = "GENERATING_ESSAY"
    DONE = "DONE"
    FAILED = "FAILED"

# Model for the data stored in MongoDB
class TaskDocument(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="_id") # Use UUID, map to _id
    task_id: uuid.UUID = Field(..., description="Public facing task identifier") # Redundant but useful for query
    video_url: HttpUrl
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    error_message: Optional[str] = None
    essay: Optional[str] = None

    class Config:
        populate_by_name = True # Allows using '_id' alias
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
             uuid.UUID: lambda u: str(u) # Ensure UUID is stored/retrieved as string if needed
            }
        # If using MongoDB directly without ODM, these help map _id
        # allow_population_by_field_name = True


# Model for the initial request response
class TaskCreationResponse(BaseModel):
    task_id: uuid.UUID

# Model for the status check response
class TaskStatusResponse(BaseModel):
    task_id: uuid.UUID
    status: TaskStatus
    updated_at: datetime.datetime

# Model for the final result response
class TaskResultResponse(BaseModel):
    task_id: uuid.UUID
    status: TaskStatus
    video_url: HttpUrl
    essay: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime