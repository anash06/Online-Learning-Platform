from fastapi import APIRouter, Depends, status, Query
from middleware.auth import RoleChecker
from schemas.user import UserRole
from services import instructor_service

router = APIRouter(prefix="/instructor", tags=["Instructor Dashboard"])

@router.get("/dashboard", response_model=dict)
async def get_dashboard_analytics(
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Fetch comprehensive instructor dashboard analytics:
    Total course counts, enrolled student count, total course revenues, course list, and recent activity logs.
    """
    response = await instructor_service.get_instructor_dashboard_analytics(
        instructor_id=current_user["id"]
    )
    return response

@router.put("/courses/{course_id}/publish", response_model=dict)
async def publish_course(
    course_id: str,
    is_published: bool = Query(..., description="Set True to publish, False to unpublish"),
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Publish or unpublish a course.
    Verifies that the course belongs to the requesting instructor (or is an Admin) and has lessons to prevent publishing empty modules.
    """
    response = await instructor_service.update_course_publish_status(
        course_id=course_id,
        is_published=is_published,
        current_user=current_user
    )
    return response
