from typing import Optional

class SummaryResponse(BaseModel):
    summary: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None