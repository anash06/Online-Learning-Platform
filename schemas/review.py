from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReviewBase(BaseModel):
    course_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    review_text: Optional[str] = Field(None, max_length=1000)

class ReviewCreate(ReviewBase):
    pass

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=1000)

class ReviewResponse(ReviewBase):
    id: str
    student_id: str
    student_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
