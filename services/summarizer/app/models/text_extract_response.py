from typing import Optional

class TextExtractionResponse(BaseModel):
    text: Optional[str] = None
    error: Optional[str] = None
    detail: Optional[str] = None