from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class LessonProgressUpdate(BaseModel):
    course_id: str
    lesson_id: str
    completed: bool = Field(True, description="Whether to mark the lesson as completed or incomplete")

class CourseProgressResponse(BaseModel):
    course_id: str
    completed_lessons: List[str] = []
    progress_percentage: float = 0.0
    updated_at: datetime

    class Config:
        from_attributes = True
