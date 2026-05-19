from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from bson import ObjectId
import logging

from database.mongodb import (
    get_wishlist_collection,
    get_courses_collection,
    get_enrollments_collection,
    get_progress_collection,
    get_reviews_collection,
    get_lessons_collection,
    get_users_collection
)
from utils.db_helpers import bson_to_dict, bson_list_to_dict_list, to_object_id
from schemas.review import ReviewCreate

logger = logging.getLogger(__name__)

# ==================== WISHLIST SERVICES ====================

async def toggle_wishlist_item(student_id: str, course_id: str) -> dict:
    """Toggle a course inside a student's wishlist (add if missing, remove if present)."""
    wishlist_coll = get_wishlist_collection()
    courses_coll = get_courses_collection()
    
    # Verify course exists
    course = await courses_coll.find_one({"_id": to_object_id(course_id)})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    wishlist = await wishlist_coll.find_one({"student_id": to_object_id(student_id)})
    now = datetime.now(timezone.utc)
    
    if not wishlist:
        # Create wishlist and add
        wishlist_doc = {
            "student_id": to_object_id(student_id),
            "course_ids": [to_object_id(course_id)],
            "updated_at": now
        }
        await wishlist_coll.insert_one(wishlist_doc)
        return bson_to_dict(wishlist_doc)
        
    course_ids = wishlist.get("course_ids", [])
    c_oid = to_object_id(course_id)
    
    if c_oid in course_ids:
        # Remove
        await wishlist_coll.update_one(
            {"student_id": to_object_id(student_id)},
            {"$pull": {"course_ids": c_oid}, "$set": {"updated_at": now}}
        )
        logger.info(f"Removed course {course_id} from wishlist of user {student_id}")
    else:
        # Add
        await wishlist_coll.update_one(
            {"student_id": to_object_id(student_id)},
            {"$addToSet": {"course_ids": c_oid}, "$set": {"updated_at": now}}
        )
        logger.info(f"Added course {course_id} to wishlist of user {student_id}")
        
    updated_wishlist = await wishlist_coll.find_one({"student_id": to_object_id(student_id)})
    return bson_to_dict(updated_wishlist)

async def get_wishlist_details(student_id: str) -> dict:
    """Fetch wishlist along with populated course details."""
    wishlist_coll = get_wishlist_collection()
    courses_coll = get_courses_collection()
    
    wishlist = await wishlist_coll.find_one({"student_id": to_object_id(student_id)})
    if not wishlist:
        return {
            "student_id": student_id,
            "course_ids": [],
            "courses": [],
            "updated_at": datetime.now(timezone.utc)
        }
        
    course_ids = wishlist.get("course_ids", [])
    courses_cursor = courses_coll.find({"_id": {"$in": course_ids}})
    courses_bson = await courses_cursor.to_list(length=100)
    
    wishlist_dict = bson_to_dict(wishlist)
    wishlist_dict["courses"] = bson_list_to_dict_list(courses_bson)
    return wishlist_dict

# ==================== ENROLLMENT & PROGRESS SERVICES ====================

async def get_student_enrollments(student_id: str) -> List[dict]:
    """Get all courses the student is currently enrolled in."""
    enrollments_coll = get_enrollments_collection()
    courses_coll = get_courses_collection()
    
    enrollments_cursor = enrollments_coll.find({
        "student_id": to_object_id(student_id),
        "status": "active"
    })
    enrollments_list = await enrollments_cursor.to_list(length=100)
    
    result = []
    for enr in enrollments_list:
        enr_dict = bson_to_dict(enr)
        course_bson = await courses_coll.find_one({"_id": enr["course_id"]})
        if course_bson:
            enr_dict["course_title"] = course_bson.get("title")
            enr_dict["course_thumbnail"] = course_bson.get("thumbnail_url")
        result.append(enr_dict)
        
    return result

async def update_lesson_progress(student_id: str, course_id: str, lesson_id: str, completed: bool) -> dict:
    """Mark a lesson complete or incomplete, and dynamically recalculate enrollment progress percentage."""
    enrollments_coll = get_enrollments_collection()
    progress_coll = get_progress_collection()
    lessons_coll = get_lessons_collection()
    
    # 1. Verify student is actually enrolled
    enrollment = await enrollments_coll.find_one({
        "student_id": to_object_id(student_id),
        "course_id": to_object_id(course_id),
        "status": "active"
    })
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course"
        )
        
    # 2. Verify lesson belongs to this course
    lesson = await lessons_coll.find_one({
        "_id": to_object_id(lesson_id),
        "course_id": to_object_id(course_id)
    })
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found in this course")
        
    now = datetime.now(timezone.utc)
    
    # 3. Update completed lessons in progress document
    operator = "$addToSet" if completed else "$pull"
    await progress_coll.update_one(
        {"student_id": to_object_id(student_id), "course_id": to_object_id(course_id)},
        {
            operator: {"completed_lessons": to_object_id(lesson_id)},
            "$set": {"updated_at": now}
        },
        upsert=True
    )
    
    # 4. Fetch updated progress to calculate percentage
    progress = await progress_coll.find_one({
        "student_id": to_object_id(student_id),
        "course_id": to_object_id(course_id)
    })
    
    completed_count = len(progress.get("completed_lessons", []))
    total_lessons = await lessons_coll.count_documents({"course_id": to_object_id(course_id)})
    
    progress_percentage = 0.0
    if total_lessons > 0:
        progress_percentage = round((completed_count / total_lessons) * 100, 2)
        
    # 5. Update progress percentage in both enrollment and progress document
    await progress_coll.update_one(
        {"_id": progress["_id"]},
        {"$set": {"progress_percentage": progress_percentage}}
    )
    
    await enrollments_coll.update_one(
        {"_id": enrollment["_id"]},
        {"$set": {"progress_percentage": progress_percentage}}
    )
    
    progress_dict = bson_to_dict(progress)
    progress_dict["progress_percentage"] = progress_percentage
    return progress_dict

async def get_course_progress(student_id: str, course_id: str) -> dict:
    """Retrieve a student's progress for a specific course."""
    progress_coll = get_progress_collection()
    lessons_coll = get_lessons_collection()
    
    progress = await progress_coll.find_one({
        "student_id": to_object_id(student_id),
        "course_id": to_object_id(course_id)
    })
    
    if not progress:
        return {
            "course_id": course_id,
            "completed_lessons": [],
            "progress_percentage": 0.0,
            "updated_at": datetime.now(timezone.utc)
        }
        
    return bson_to_dict(progress)

# ==================== REVIEW SERVICES ====================

async def recalculate_course_rating(course_id: ObjectId):
    """Aggregate rating average and count in courses collection."""
    reviews_coll = get_reviews_collection()
    courses_coll = get_courses_collection()
    
    # Fetch all ratings for course
    reviews_cursor = reviews_coll.find({"course_id": course_id})
    reviews = await reviews_cursor.to_list(length=10000)
    
    ratings_count = len(reviews)
    average_rating = 0.0
    
    if ratings_count > 0:
        total_score = sum([r["rating"] for r in reviews])
        average_rating = round(total_score / ratings_count, 1)
        
    await courses_coll.update_one(
        {"_id": course_id},
        {"$set": {"average_rating": average_rating, "ratings_count": ratings_count}}
    )

async def add_course_review(student_id: str, student_name: str, review_data: ReviewCreate) -> dict:
    """Post a course review (only allowed for enrolled students; upserts if already reviewed)."""
    reviews_coll = get_reviews_collection()
    enrollments_coll = get_enrollments_collection()
    
    course_oid = to_object_id(review_data.course_id)
    student_oid = to_object_id(student_id)
    
    # 1. Enforce student enrollment
    enrolled = await enrollments_coll.find_one({
        "student_id": student_oid,
        "course_id": course_oid,
        "status": "active"
    })
    if not enrolled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in this course to leave a review"
        )
        
    now = datetime.now(timezone.utc)
    
    # 2. Upsert review
    existing_review = await reviews_coll.find_one({
        "student_id": student_oid,
        "course_id": course_oid
    })
    
    if existing_review:
        await reviews_coll.update_one(
            {"_id": existing_review["_id"]},
            {
                "$set": {
                    "rating": review_data.rating,
                    "review_text": review_data.review_text,
                    "updated_at": now
                }
            }
        )
        review_doc = await reviews_coll.find_one({"_id": existing_review["_id"]})
    else:
        review_doc = {
            "student_id": student_oid,
            "student_name": student_name,
            "course_id": course_oid,
            "rating": review_data.rating,
            "review_text": review_data.review_text,
            "created_at": now,
            "updated_at": now
        }
        result = await reviews_coll.insert_one(review_doc)
        review_doc["_id"] = result.inserted_id
        
    # 3. Recalculate average rating for course
    await recalculate_course_rating(course_oid)
    
    return bson_to_dict(review_doc)

async def list_course_reviews(course_id: str) -> List[dict]:
    """Retrieve all reviews posted for a specific course."""
    reviews_coll = get_reviews_collection()
    reviews_cursor = reviews_coll.find({"course_id": to_object_id(course_id)}).sort("updated_at", -1)
    reviews_list = await reviews_cursor.to_list(length=500)
    return bson_list_to_dict_list(reviews_list)
