from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from bson import ObjectId
import logging

from database.mongodb import (
    get_users_collection,
    get_courses_collection,
    get_enrollments_collection,
    get_payments_collection
)
from utils.db_helpers import bson_to_dict, bson_list_to_dict_list, to_object_id
from schemas.user import UserRole

logger = logging.getLogger(__name__)

async def get_admin_dashboard_statistics() -> dict:
    """Retrieve platform-wide statistics for the admin dashboard."""
    users_coll = get_users_collection()
    courses_coll = get_courses_collection()
    enrollments_coll = get_enrollments_collection()
    payments_coll = get_payments_collection()
    
    # 1. User counts
    total_users = await users_coll.count_documents({})
    total_students = await users_coll.count_documents({"role": UserRole.STUDENT.value})
    total_instructors = await users_coll.count_documents({"role": UserRole.INSTRUCTOR.value})
    total_admins = await users_coll.count_documents({"role": UserRole.ADMIN.value})
    
    # 2. Course & Enrollment counts
    total_courses = await courses_coll.count_documents({})
    published_courses = await courses_coll.count_documents({"is_published": True})
    total_enrollments = await enrollments_coll.count_documents({"status": "active"})
    
    # 3. Revenue calculation
    total_revenue = 0.0
    revenue_pipeline = [
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
    ]
    rev_cursor = payments_coll.aggregate(revenue_pipeline)
    rev_result = await rev_cursor.to_list(length=1)
    if rev_result:
        total_revenue = round(rev_result[0]["total"], 2)
        
    return {
        "users": {
            "total_users": total_users,
            "total_students": total_students,
            "total_instructors": total_instructors,
            "total_admins": total_admins
        },
        "courses": {
            "total_courses": total_courses,
            "published_courses": published_courses,
            "total_enrollments": total_enrollments
        },
        "revenue": {
            "total_revenue": total_revenue,
            "currency": "INR"
        }
    }

async def list_all_users(role: Optional[str] = None, page: int = 1, limit: int = 20) -> Tuple[List[dict], int]:
    """Retrieve all users in the system, optionally filtered by role, with pagination."""
    users_coll = get_users_collection()
    query = {}
    
    if role:
        query["role"] = role
        
    skip = (page - 1) * limit
    total = await users_coll.count_documents(query)
    
    # Do not return sensitive password hashes in query output
    cursor = users_coll.find(query, {"hashed_password": 0, "reset_otp": 0, "reset_otp_expiry": 0}).sort("created_at", -1).skip(skip).limit(limit)
    users_bson = await cursor.to_list(length=limit)
    
    return bson_list_to_dict_list(users_bson), total

async def toggle_user_active_status(user_id: str, is_active: bool) -> dict:
    """Ban/Deactivate or Reactivate a user account."""
    users_coll = get_users_collection()
    
    user = await users_coll.find_one({"_id": to_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
        
    if user.get("role") == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot toggle active status of an admin account"
        )
        
    await users_coll.update_one(
        {"_id": to_object_id(user_id)},
        {"$set": {"is_active": is_active, "updated_at": datetime.now(timezone.utc)}}
    )
    
    status_str = "activated" if is_active else "deactivated (banned)"
    return {"message": f"User account has been successfully {status_str}", "user_id": user_id, "is_active": is_active}

async def delete_user_account(user_id: str) -> dict:
    """Permanently delete a user account and clean up enrollments."""
    users_coll = get_users_collection()
    enrollments_coll = get_enrollments_collection()
    
    user = await users_coll.find_one({"_id": to_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
        
    if user.get("role") == UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an admin account through API"
        )
        
    # Cascade cleanups
    if user.get("role") == UserRole.STUDENT.value:
        # Cancel enrollments rather than deleting to preserve course stats and invoice records
        await enrollments_coll.update_many(
            {"student_id": to_object_id(user_id)},
            {"$set": {"status": "inactive_deleted"}}
        )
    elif user.get("role") == UserRole.INSTRUCTOR.value:
        courses_coll = get_courses_collection()
        course_count = await courses_coll.count_documents({"instructor_id": to_object_id(user_id)})
        if course_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete instructor with active courses. Reassign or delete courses first."
            )
            
    await users_coll.delete_one({"_id": to_object_id(user_id)})
    return {"message": "User account permanently deleted"}

async def list_payments_history(page: int = 1, limit: int = 20) -> Tuple[List[dict], int]:
    """Retrieve full chronological transaction records across the platform, populating details."""
    payments_coll = get_payments_collection()
    users_coll = get_users_collection()
    courses_coll = get_courses_collection()
    
    skip = (page - 1) * limit
    total = await payments_coll.count_documents({})
    
    cursor = payments_coll.find({}).sort("created_at", -1).skip(skip).limit(limit)
    payments_bson = await cursor.to_list(length=limit)
    
    payments_dict = bson_list_to_dict_list(payments_bson)
    
    # Populate user and course details
    for pay in payments_dict:
        student = await users_coll.find_one({"_id": to_object_id(pay["student_id"])})
        course = await courses_coll.find_one({"_id": to_object_id(pay["course_id"])})
        
        pay["student_name"] = student.get("full_name") if student else "Unknown Student"
        pay["student_email"] = student.get("email") if student else ""
        pay["course_title"] = course.get("title") if course else "Unknown Course"
        
    return payments_dict, total
