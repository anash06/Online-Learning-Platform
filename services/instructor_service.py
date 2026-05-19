from datetime import datetime, timezone
from typing import List, Dict
from fastapi import HTTPException, status
from bson import ObjectId
import logging

from database.mongodb import (
    get_courses_collection,
    get_enrollments_collection,
    get_payments_collection,
    get_users_collection
)
from utils.db_helpers import bson_to_dict, bson_list_to_dict_list, to_object_id
from services.course_service import verify_course_owner_or_admin

logger = logging.getLogger(__name__)

async def get_instructor_dashboard_analytics(instructor_id: str) -> dict:
    """Retrieve aggregate statistics and recent activities for an instructor's courses."""
    courses_coll = get_courses_collection()
    enrollments_coll = get_enrollments_collection()
    payments_coll = get_payments_collection()
    users_coll = get_users_collection()
    
    inst_oid = to_object_id(instructor_id)
    
    # 1. Fetch all courses by instructor
    courses_cursor = courses_coll.find({"instructor_id": inst_oid})
    courses = await courses_cursor.to_list(length=1000)
    course_dicts = bson_list_to_dict_list(courses)
    
    course_oids = [c["_id"] for c in courses]
    course_id_strs = [str(c["_id"]) for c in courses]
    
    # Defaults
    total_courses = len(courses)
    total_students = 0
    total_revenue = 0.0
    average_course_rating = 0.0
    
    if total_courses > 0:
        # 2. Total enrolled students (active enrollments)
        total_students = await enrollments_coll.count_documents({
            "course_id": {"$in": course_oids},
            "status": "active"
        })
        
        # 3. Total revenue from successful payments
        revenue_pipeline = [
            {"$match": {"course_id": {"$in": course_oids}, "status": "success"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        rev_cursor = payments_coll.aggregate(revenue_pipeline)
        rev_result = await rev_cursor.to_list(length=1)
        if rev_result:
            total_revenue = round(rev_result[0]["total"], 2)
            
        # 4. Average rating across all courses
        ratings = [c["average_rating"] for c in course_dicts if c.get("ratings_count", 0) > 0]
        if ratings:
            average_course_rating = round(sum(ratings) / len(ratings), 1)
            
    # 5. Fetch recent enrollments (limit 5)
    recent_enrollments = []
    if total_courses > 0:
        recent_cursor = enrollments_coll.find({
            "course_id": {"$in": course_oids},
            "status": "active"
        }).sort("enrolled_at", -1).limit(5)
        
        recent_list = await recent_cursor.to_list(length=5)
        for enr in recent_list:
            student = await users_coll.find_one({"_id": enr["student_id"]})
            course = await courses_coll.find_one({"_id": enr["course_id"]})
            
            student_name = student.get("full_name", "Unknown Student") if student else "Unknown Student"
            student_email = student.get("email", "") if student else ""
            course_title = course.get("title", "Unknown Course") if course else "Unknown Course"
            
            recent_enrollments.append({
                "enrollment_id": str(enr["_id"]),
                "student_name": student_name,
                "student_email": student_email,
                "course_title": course_title,
                "enrolled_at": enr.get("enrolled_at")
            })
            
    return {
        "analytics": {
            "total_courses": total_courses,
            "total_students": total_students,
            "total_revenue": total_revenue,
            "average_course_rating": average_course_rating
        },
        "courses": course_dicts,
        "recent_enrollments": recent_enrollments
    }

async def update_course_publish_status(course_id: str, is_published: bool, current_user: dict) -> dict:
    """Publish or unpublish a course (only allowed for the course's instructor or an admin)."""
    # Verifies owner or admin
    await verify_course_owner_or_admin(course_id, current_user)
    
    courses_coll = get_courses_collection()
    
    # If publishing, verify it has at least one section and one lesson to prevent publishing empty courses
    if is_published:
        sections_coll = get_sections_collection()
        lessons_coll = get_lessons_collection()
        
        section_count = await sections_coll.count_documents({"course_id": to_object_id(course_id)})
        lesson_count = await lessons_coll.count_documents({"course_id": to_object_id(course_id)})
        
        if section_count == 0 or lesson_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish an empty course. Please add at least one section and one lesson first."
            )
            
    now = datetime.now(timezone.utc)
    await courses_coll.update_one(
        {"_id": to_object_id(course_id)},
        {"$set": {"is_published": is_published, "updated_at": now}}
    )
    
    status_str = "published" if is_published else "unpublished"
    return {"message": f"Course successfully {status_str}", "is_published": is_published}
