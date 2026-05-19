from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EnrollmentResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    course_title: Optional[str] = None
    course_thumbnail: Optional[str] = None
    enrolled_at: datetime
    progress_percentage: float = 0.0
    status: str = "active"  # active, refunded

    class Config:
        from_attributes = True
