from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional

from middleware.auth import RoleChecker
from schemas.user import UserRole
from services import admin_service, course_service

router = APIRouter(prefix="/admin", tags=["Admin Module"])

# Enforce Admin Role checking on all routes under this router
admin_dependency = Depends(RoleChecker([UserRole.ADMIN]))

@router.get("/stats", response_model=dict, dependencies=[admin_dependency])
async def get_stats():
    """
    Get global platform stats (net revenue, courses counts, student/instructor ratio).
    """
    stats = await admin_service.get_admin_dashboard_statistics()
    return stats

@router.get("/users", response_model=dict, dependencies=[admin_dependency])
async def list_users(
    role: Optional[str] = Query(None, description="Filter users by role (student, instructor, admin)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    List all users in the system with pagination and role filters.
    Sensitive credential fields are excluded.
    """
    users, total = await admin_service.list_all_users(role=role, page=page, limit=limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "results": users
    }

@router.put("/users/{user_id}/status", response_model=dict, dependencies=[admin_dependency])
async def toggle_user_status(
    user_id: str,
    is_active: bool = Query(..., description="Set False to ban/deactivate user, True to reactivate")
):
    """
    Ban/deactivate or reactivate a user's account.
    Prevents deactivating Admin accounts.
    """
    response = await admin_service.toggle_user_active_status(user_id=user_id, is_active=is_active)
    return response

@router.delete("/users/{user_id}", response_model=dict, dependencies=[admin_dependency])
async def delete_user(user_id: str):
    """
    Permanently delete a user account and associated student/instructor data cascades safely.
    """
    response = await admin_service.delete_user_account(user_id=user_id)
    return response

@router.get("/payments", response_model=dict, dependencies=[admin_dependency])
async def get_all_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get platform-wide billing/transaction histories with student and course details populated.
    """
    payments, total = await admin_service.list_payments_history(page=page, limit=limit)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "results": payments
    }

@router.delete("/courses/{course_id}", response_model=dict, dependencies=[admin_dependency])
async def remove_inappropriate_content(course_id: str, current_user: dict = Depends(RoleChecker([UserRole.ADMIN]))):
    """
    Administrative deletion of any course for content policy violations.
    Bypasses enrollment blocks to ensure swift removal by the Admin.
    """
    # Delete courses directly
    response = await course_service.delete_course(course_id=course_id, current_user=current_user)
    return response
