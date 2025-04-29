# app/models/request.py
import uuid
from pydantic import Field
from pydantic import BaseModel

class TaskRequest(BaseModel):
    """Request model for testing document extraction."""
    jwt_token: str = Field(..., description="JWT token for authentication")
    summary_id: uuid.UUID = Field(..., description="ID of the summary in DB")
    uploaded_file_name: str = Field(..., description="Name of the file once is uploaded")
    folder_name: str = Field(None, description="Name of the folder where the file is stored")
