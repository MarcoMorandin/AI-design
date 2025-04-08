# app/models/summary.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import datetime
import uuid

class DocumentInfo(BaseModel):
    """Information about the document being summarized."""
    filename: str
    file_path: str
    file_type: str
    page_count: Optional[int] = None
    word_count: Optional[int] = None

class SummaryContent(BaseModel):
    """Content of the document summary."""
    executive_summary: str
    comprehensive_summary: str
    key_points: List[str]
    important_facts: List[str]
    conclusions: List[str]
    terminology: Dict[str, str] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)

class SummaryDocument(BaseModel):
    """Database model for a document summary."""
    summary_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    task_id: uuid.UUID
    document_info: DocumentInfo
    content: SummaryContent
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    class Config:
        populate_by_name = True
        json_encoders = {
            uuid.UUID: str,
            datetime.datetime: lambda v: v.isoformat()
        }