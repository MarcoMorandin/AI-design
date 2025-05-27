from pydantic import BaseModel
from typing import List, Optional, Dict, Any, ForwardRef
from datetime import datetime

# Forward reference for recursive structure
FolderItemRef = ForwardRef('FolderItem')

class FolderItem(BaseModel):
    id: str
    name: str
    mime_type: str
    is_folder: bool
    children: Optional[List[FolderItemRef]] = []

# Update forward reference
FolderItem.model_rebuild()

class UserProfile(BaseModel):
    user_id: str
    google_id: str
    email: str
    display_name: str
    drive_folder_id: Optional[str] = None
    drive_folder_name: Optional[str] = None
    created_at: Optional[datetime] = None

class FolderStructure(BaseModel):
    folder_id: str
    folder_name: str
    items: List[FolderItem]

class Course(BaseModel):
    id: str
    name: str

class CourseList(BaseModel):
    courses: List[Course]

class CourseFolderStructure(BaseModel):
    course_id: str
    course_name: str
    items: List[FolderItem]

class OrchestratorMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str
    params: Optional[Dict[str, Any]] = None

class OrchestratorResponse(BaseModel):
    task_id: str
    status: str
    
class TaskStatusResponse(BaseModel):
    status: str
    content: Optional[str] = None
    error: Optional[str] = None
