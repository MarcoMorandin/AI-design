from pydantic import BaseModel
from typing import Optional

class EssayResponse(BaseModel):
    essay: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None