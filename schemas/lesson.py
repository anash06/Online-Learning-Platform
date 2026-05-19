from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LessonBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    video_url: Optional[str] = None
    duration: float = Field(0.0, description="Duration in minutes")
    order: int = Field(1, description="Order of the lesson inside the section")
    is_preview: bool = Field(False, description="Whether this lesson can be watched without enrolling")
    content_type: str = Field("video", description="video or article")
    text_content: Optional[str] = None

class LessonCreate(LessonBase):
    pass

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    video_url: Optional[str] = None
    duration: Optional[float] = None
    order: Optional[int] = None
    is_preview: Optional[bool] = None
    content_type: Optional[str] = None
    text_content: Optional[str] = None

class LessonResponse(LessonBase):
    id: str
    section_id: str
    course_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
