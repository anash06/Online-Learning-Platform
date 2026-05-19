from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from schemas.course import CourseResponse

class WishlistToggle(BaseModel):
    course_id: str

class WishlistResponse(BaseModel):
    id: str
    student_id: str
    course_ids: List[str] = []
    updated_at: datetime

    class Config:
        from_attributes = True

class WishlistDetailResponse(WishlistResponse):
    courses: List[CourseResponse] = []
