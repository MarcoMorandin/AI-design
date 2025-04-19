# app/models/request.py
import uuid
from pydantic import Field
from pydantic import BaseModel, FilePath, DirectoryPath
from typing import Optional, Union
from enum import Enum

class TaskRequest(BaseModel):
    """Request model for testing document extraction."""
    summaryId: uuid.UUID = Field(..., description="ID of the summary in DB")
    uploaded_file_name: str = Field(..., description="Name of the file once is uploaded")
