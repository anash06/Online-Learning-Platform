from fastapi import APIRouter, Depends, status
from typing import List

from schemas.enrollment import EnrollmentResponse
from schemas.progress import CourseProgressResponse, LessonProgressUpdate
from middleware.auth import get_current_user
from services import student_service

router = APIRouter(prefix="/enrollments", tags=["Enrollments & Progress"])

@router.get("/", response_model=List[EnrollmentResponse])
async def get_my_courses(current_user: dict = Depends(get_current_user)):
    """
    Get a list of all courses the student is currently enrolled in.
    """
    enrollments = await student_service.get_student_enrollments(student_id=current_user["id"])
    return enrollments

@router.get("/{course_id}/progress", response_model=CourseProgressResponse)
async def get_progress(course_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fetch the student's lesson completion progress for a specific course.
    """
    progress = await student_service.get_course_progress(
        student_id=current_user["id"],
        course_id=course_id
    )
    return progress

@router.put("/{course_id}/progress", response_model=CourseProgressResponse)
async def update_progress(
    progress_data: LessonProgressUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a lesson as completed or incomplete.
    Automatically recalculates overall progress percentage.
    """
    progress = await student_service.update_lesson_progress(
        student_id=current_user["id"],
        course_id=progress_data.course_id,
        lesson_id=progress_data.lesson_id,
        completed=progress_data.completed
    )
    return progress
