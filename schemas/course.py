from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from schemas.section import SectionResponse

class CourseLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"

class CourseBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=150)
    description: str = Field(..., min_length=20)
    price: float = Field(0.0, ge=0.0)
    category_id: str
    level: CourseLevel = CourseLevel.BEGINNER
    tags: List[str] = []

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    level: Optional[CourseLevel] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    thumbnail_url: Optional[str] = None

class CourseResponse(CourseBase):
    id: str
    instructor_id: str
    instructor_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_published: bool = False
    average_rating: float = 0.0
    ratings_count: int = 0
    enrollment_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CourseDetailResponse(CourseResponse):
    sections: List[SectionResponse] = []
