from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from schemas.lesson import LessonResponse

class SectionBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    order: int = Field(1, description="Order of the section inside the course")

class SectionCreate(SectionBase):
    pass

class SectionUpdate(BaseModel):
    title: Optional[str] = None
    order: Optional[int] = None

class SectionResponse(SectionBase):
    id: str
    course_id: str
    lessons: List[LessonResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
