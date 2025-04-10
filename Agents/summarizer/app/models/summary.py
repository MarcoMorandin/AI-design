from typing import Optional

class SummaryResponse(BaseModel):
    essay: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None