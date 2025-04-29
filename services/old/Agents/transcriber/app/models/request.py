# app/models/request.py
from pydantic import BaseModel, HttpUrl, Field

class VideoUrlRequest(BaseModel):
    video_url: HttpUrl = Field(..., description="URL of the video file to process (must be publicly accessible).")