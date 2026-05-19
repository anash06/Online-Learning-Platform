from fastapi import APIRouter, Depends, status, HTTPException
from typing import List

from schemas.review import ReviewCreate, ReviewResponse
from middleware.auth import get_current_user
from services import student_service

router = APIRouter(prefix="/reviews", tags=["Course Reviews"])

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_data: ReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit a review and rating (1-5) for a course.
    Only students currently enrolled in the course are authorized.
    Updates or inserts a single review per student/course.
    """
    review = await student_service.add_course_review(
        student_id=current_user["id"],
        student_name=current_user["full_name"],
        review_data=review_data
    )
    return review

@router.get("/course/{course_id}", response_model=List[ReviewResponse])
async def get_reviews(course_id: str):
    """
    Publicly get all ratings and reviews submitted for a specific course.
    """
    reviews = await student_service.list_course_reviews(course_id=course_id)
    return reviews
