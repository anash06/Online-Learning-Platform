from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from bson import ObjectId
import logging

from database.mongodb import (
    get_courses_collection,
    get_sections_collection,
    get_lessons_collection,
    get_categories_collection,
    get_enrollments_collection
)
from utils.db_helpers import bson_to_dict, bson_list_to_dict_list, to_object_id
from schemas.course import CourseCreate, CourseUpdate
from schemas.section import SectionCreate, SectionUpdate
from schemas.lesson import LessonCreate, LessonUpdate
from schemas.user import UserRole

logger = logging.getLogger(__name__)

async def verify_course_owner_or_admin(course_id: str, current_user: dict):
    """Utility helper to ensure a user is either the instructor of the course or an admin."""
    courses_coll = get_courses_collection()
    course = await courses_coll.find_one({"_id": to_object_id(course_id)})
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Allow if Admin, or if current user is the Instructor of the course
    if current_user.get("role") == UserRole.ADMIN.value:
        return course
        
    if str(course.get("instructor_id")) != current_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not the instructor of this course"
        )
    return course

# ==================== COURSE SERVICES ====================

async def create_course(course_data: CourseCreate, instructor_id: str, instructor_name: str) -> dict:
    """Create a new course."""
    courses_coll = get_courses_collection()
    categories_coll = get_categories_collection()
    
    # Validate category exists
    category = await categories_coll.find_one({"_id": to_object_id(course_data.category_id)})
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
        
    now = datetime.now(timezone.utc)
    course_doc = {
        "title": course_data.title,
        "description": course_data.description,
        "price": course_data.price,
        "category_id": to_object_id(course_data.category_id),
        "level": course_data.level.value,
        "tags": course_data.tags,
        "instructor_id": to_object_id(instructor_id),
        "instructor_name": instructor_name,
        "thumbnail_url": None,
        "is_published": False,
        "average_rating": 0.0,
        "ratings_count": 0,
        "enrollment_count": 0,
        "created_at": now,
        "updated_at": now
    }
    
    result = await courses_coll.insert_one(course_doc)
    course_doc["_id"] = result.inserted_id
    
    return bson_to_dict(course_doc)

async def get_course_details(course_id: str) -> dict:
    """Fetch a course with nested sections and lessons recursively populated."""
    courses_coll = get_courses_collection()
    sections_coll = get_sections_collection()
    lessons_coll = get_lessons_collection()
    
    course_bson = await courses_coll.find_one({"_id": to_object_id(course_id)})
    if not course_bson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
        
    course_dict = bson_to_dict(course_bson)
    
    # Fetch sections sorted by order
    sections_cursor = sections_coll.find({"course_id": to_object_id(course_id)}).sort("order", 1)
    sections_list = await sections_cursor.to_list(length=100)
    sections_dict_list = bson_list_to_dict_list(sections_list)
    
    # Fetch lessons for this course
    lessons_cursor = lessons_coll.find({"course_id": to_object_id(course_id)}).sort("order", 1)
    lessons_list = await lessons_cursor.to_list(length=1000)
    lessons_dict_list = bson_list_to_dict_list(lessons_list)
    
    # Group lessons by section_id
    lessons_by_section = {}
    for lesson in lessons_dict_list:
        sec_id = lesson.get("section_id")
        if sec_id not in lessons_by_section:
            lessons_by_section[sec_id] = []
        lessons_by_section[sec_id].append(lesson)
        
    # Nest lessons inside sections
    for sec in sections_dict_list:
        sec_id = sec.get("id")
        sec["lessons"] = lessons_by_section.get(sec_id, [])
        
    course_dict["sections"] = sections_dict_list
    return course_dict

async def update_course(course_id: str, update_data: CourseUpdate, current_user: dict) -> dict:
    """Update course details."""
    await verify_course_owner_or_admin(course_id, current_user)
    courses_coll = get_courses_collection()
    
    update_dict = update_data.model_dump(exclude_unset=True)
    if "category_id" in update_dict:
        categories_coll = get_categories_collection()
        category = await categories_coll.find_one({"_id": to_object_id(update_dict["category_id"])})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        update_dict["category_id"] = to_object_id(update_dict["category_id"])
        
    if "level" in update_dict and update_dict["level"]:
        update_dict["level"] = update_dict["level"].value
        
    if not update_dict:
        # Nothing to update, return details
        return await get_course_details(course_id)
        
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    await courses_coll.update_one(
        {"_id": to_object_id(course_id)},
        {"$set": update_dict}
    )
    
    return await get_course_details(course_id)

async def delete_course(course_id: str, current_user: dict) -> dict:
    """Delete a course and all associated sections and lessons."""
    await verify_course_owner_or_admin(course_id, current_user)
    
    courses_coll = get_courses_collection()
    sections_coll = get_sections_collection()
    lessons_coll = get_lessons_collection()
    enrollments_coll = get_enrollments_collection()
    
    # 1. Check if course has active enrollments (cannot delete if it does)
    enrollment = await enrollments_coll.find_one({"course_id": to_object_id(course_id), "status": "active"})
    if enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete course with active student enrollments. Unpublish it instead."
        )
        
    # 2. Delete all lessons
    await lessons_coll.delete_many({"course_id": to_object_id(course_id)})
    
    # 3. Delete all sections
    await sections_coll.delete_many({"course_id": to_object_id(course_id)})
    
    # 4. Delete course
    await courses_coll.delete_one({"_id": to_object_id(course_id)})
    
    return {"message": "Course and all related sections and lessons deleted successfully"}

async def list_courses(
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    level: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_published: Optional[bool] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> Tuple[List[dict], int]:
    """Search, filter, paginate and sort courses."""
    courses_coll = get_courses_collection()
    query = {}
    
    # Filter conditions
    if is_published is not None:
        query["is_published"] = is_published
        
    if category_id:
        try:
            query["category_id"] = to_object_id(category_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Category ID format")
            
    if level:
        query["level"] = level
        
    if min_price is not None or max_price is not None:
        price_query = {}
        if min_price is not None:
            price_query["$gte"] = min_price
        if max_price is not None:
            price_query["$lte"] = max_price
        query["price"] = price_query
        
    if search:
        # Full text search or regex matching on title/description/tags
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
        
    # Sorting
    sort_field = "created_at"
    sort_direction = -1
    
    if sort_by == "price_asc":
        sort_field = "price"
        sort_direction = 1
    elif sort_by == "price_desc":
        sort_field = "price"
        sort_direction = -1
    elif sort_by == "rating":
        sort_field = "average_rating"
        sort_direction = -1
    elif sort_by == "popularity":
        sort_field = "enrollment_count"
        sort_direction = -1
        
    skip = (page - 1) * limit
    
    total = await courses_coll.count_documents(query)
    cursor = courses_coll.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
    courses_bson = await cursor.to_list(length=limit)
    
    return bson_list_to_dict_list(courses_bson), total

# ==================== SECTION SERVICES ====================

async def create_section(course_id: str, section_data: SectionCreate, current_user: dict) -> dict:
    """Create a new section inside a course."""
    await verify_course_owner_or_admin(course_id, current_user)
    sections_coll = get_sections_collection()
    
    now = datetime.now(timezone.utc)
    section_doc = {
        "course_id": to_object_id(course_id),
        "title": section_data.title,
        "order": section_data.order,
        "created_at": now,
        "updated_at": now
    }
    
    result = await sections_coll.insert_one(section_doc)
    section_doc["_id"] = result.inserted_id
    
    # Return populated section
    section_dict = bson_to_dict(section_doc)
    section_dict["lessons"] = []
    return section_dict

async def update_section(course_id: str, section_id: str, update_data: SectionUpdate, current_user: dict) -> dict:
    """Update section details."""
    await verify_course_owner_or_admin(course_id, current_user)
    sections_coll = get_sections_collection()
    
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    result = await sections_coll.update_one(
        {"_id": to_object_id(section_id), "course_id": to_object_id(course_id)},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Section not found in this course")
        
    # Get details
    section_bson = await sections_coll.find_one({"_id": to_object_id(section_id)})
    
    # Attach lessons
    lessons_coll = get_lessons_collection()
    lessons_cursor = lessons_coll.find({"section_id": to_object_id(section_id)}).sort("order", 1)
    lessons_list = await lessons_cursor.to_list(length=100)
    
    section_dict = bson_to_dict(section_bson)
    section_dict["lessons"] = bson_list_to_dict_list(lessons_list)
    return section_dict

async def delete_section(course_id: str, section_id: str, current_user: dict) -> dict:
    """Delete a section and all of its lessons."""
    await verify_course_owner_or_admin(course_id, current_user)
    sections_coll = get_sections_collection()
    lessons_coll = get_lessons_collection()
    
    # Delete lessons belonging to this section
    await lessons_coll.delete_many({
        "course_id": to_object_id(course_id),
        "section_id": to_object_id(section_id)
    })
    
    # Delete section itself
    result = await sections_coll.delete_one({
        "_id": to_object_id(section_id),
        "course_id": to_object_id(course_id)
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Section not found in this course")
        
    return {"message": "Section and all nested lessons deleted successfully"}

# ==================== LESSON SERVICES ====================

async def create_lesson(course_id: str, section_id: str, lesson_data: LessonCreate, current_user: dict) -> dict:
    """Create a new lesson in a section."""
    await verify_course_owner_or_admin(course_id, current_user)
    sections_coll = get_sections_collection()
    lessons_coll = get_lessons_collection()
    
    # Validate section exists
    section = await sections_coll.find_one({"_id": to_object_id(section_id), "course_id": to_object_id(course_id)})
    if not section:
        raise HTTPException(status_code=404, detail="Section not found in this course")
        
    now = datetime.now(timezone.utc)
    lesson_doc = {
        "course_id": to_object_id(course_id),
        "section_id": to_object_id(section_id),
        "title": lesson_data.title,
        "video_url": lesson_data.video_url,
        "duration": lesson_data.duration,
        "order": lesson_data.order,
        "is_preview": lesson_data.is_preview,
        "content_type": lesson_data.content_type,
        "text_content": lesson_data.text_content,
        "created_at": now,
        "updated_at": now
    }
    
    result = await lessons_coll.insert_one(lesson_doc)
    lesson_doc["_id"] = result.inserted_id
    
    return bson_to_dict(lesson_doc)

async def update_lesson(
    course_id: str,
    section_id: str,
    lesson_id: str,
    update_data: LessonUpdate,
    current_user: dict
) -> dict:
    """Update lesson details."""
    await verify_course_owner_or_admin(course_id, current_user)
    lessons_coll = get_lessons_collection()
    
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
        
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    result = await lessons_coll.update_one(
        {
            "_id": to_object_id(lesson_id),
            "section_id": to_object_id(section_id),
            "course_id": to_object_id(course_id)
        },
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lesson not found in this section/course")
        
    lesson_bson = await lessons_coll.find_one({"_id": to_object_id(lesson_id)})
    return bson_to_dict(lesson_bson)

async def delete_lesson(course_id: str, section_id: str, lesson_id: str, current_user: dict) -> dict:
    """Delete a lesson."""
    await verify_course_owner_or_admin(course_id, current_user)
    lessons_coll = get_lessons_collection()
    
    result = await lessons_coll.delete_one({
        "_id": to_object_id(lesson_id),
        "section_id": to_object_id(section_id),
        "course_id": to_object_id(course_id)
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lesson not found in this section/course")
        
    return {"message": "Lesson deleted successfully"}
