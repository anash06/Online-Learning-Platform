from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from typing import List, Optional
import os
import uuid
import shutil

from schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse
from schemas.section import SectionCreate, SectionUpdate, SectionResponse
from schemas.lesson import LessonCreate, LessonUpdate, LessonResponse
from schemas.category import CategoryCreate, CategoryResponse
from middleware.auth import get_current_user, RoleChecker
from schemas.user import UserRole
from services import course_service
from database.mongodb import get_categories_collection, get_courses_collection, get_lessons_collection
from utils.db_helpers import bson_to_dict, bson_list_to_dict_list, to_object_id
from config.config import settings

router = APIRouter(prefix="/courses", tags=["Courses Module"])

# ==================== CATEGORIES ENDPOINTS ====================

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_new_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(RoleChecker([UserRole.ADMIN]))
):
    """
    Create a new course category.
    Accessible only by Admins.
    """
    categories_coll = get_categories_collection()
    
    # Check if category name already exists
    existing = await categories_coll.find_one({"name": {"$regex": f"^{category_data.name}$", "$options": "i"}})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
        
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    category_doc = {
        "name": category_data.name,
        "description": category_data.description,
        "created_at": now,
        "updated_at": now
    }
    
    result = await categories_coll.insert_one(category_doc)
    category_doc["_id"] = result.inserted_id
    return bson_to_dict(category_doc)

@router.get("/categories", response_model=List[CategoryResponse])
async def list_all_categories():
    """
    Get a list of all course categories.
    Accessible publicly.
    """
    categories_coll = get_categories_collection()
    cursor = categories_coll.find({}).sort("name", 1)
    cats = await cursor.to_list(length=100)
    return bson_list_to_dict_list(cats)

# ==================== COURSE CRUD ENDPOINTS ====================

@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Create a new course.
    Accessible by Instructors and Admins.
    """
    course = await course_service.create_course(
        course_data,
        instructor_id=current_user["id"],
        instructor_name=current_user["full_name"]
    )
    return course

@router.get("/", response_model=dict)
async def get_courses(
    search: Optional[str] = Query(None, description="Search courses by title, description or tags"),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    level: Optional[str] = Query(None, description="Filter by level (Beginner/Intermediate/Advanced)"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    sort_by: Optional[str] = Query(None, description="Sort options: price_asc, price_desc, rating, popularity"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Public search, filter, paginate, and list published courses.
    """
    # Public route should filter by is_published = True
    courses, total = await course_service.list_courses(
        search=search,
        category_id=category_id,
        level=level,
        min_price=min_price,
        max_price=max_price,
        is_published=True,
        sort_by=sort_by,
        page=page,
        limit=limit
    )
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "results": courses
    }

@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_course_details(course_id: str):
    """
    Publicly get detailed course information including all populated sections and lessons.
    """
    course = await course_service.get_course_details(course_id)
    return course

@router.put("/{course_id}", response_model=CourseDetailResponse)
async def update_course(
    course_id: str,
    update_data: CourseUpdate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Update course details.
    Accessible only by the course's Instructor owner or an Admin.
    """
    course = await course_service.update_course(course_id, update_data, current_user)
    return course

@router.delete("/{course_id}", status_code=status.HTTP_200_OK)
async def delete_course(
    course_id: str,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Delete a course, its sections, and its lessons.
    Cannot be deleted if it has active enrollments (unpublish instead).
    Accessible only by the course's Instructor owner or an Admin.
    """
    response = await course_service.delete_course(course_id, current_user)
    return response

# ==================== COURSE FILE UPLOADS ====================

@router.post("/{course_id}/upload-thumbnail", response_model=CourseResponse)
async def upload_course_thumbnail(
    course_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Upload a course image thumbnail and save it locally.
    Updates the course thumbnail URL.
    Accessible only by the course's Instructor owner or an Admin.
    """
    # Verify ownership
    await course_service.verify_course_owner_or_admin(course_id, current_user)
    
    # Check mime type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed for thumbnails")
        
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"thumb_{course_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    thumbnail_url = f"/static/uploads/{unique_filename}"
    
    courses_coll = get_courses_collection()
    from datetime import datetime, timezone
    await courses_coll.update_one(
        {"_id": to_object_id(course_id)},
        {"$set": {"thumbnail_url": thumbnail_url, "updated_at": datetime.now(timezone.utc)}}
    )
    
    course_bson = await courses_coll.find_one({"_id": to_object_id(course_id)})
    return bson_to_dict(course_bson)

# ==================== SECTION ENDPOINTS ====================

@router.post("/{course_id}/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
async def create_section(
    course_id: str,
    section_data: SectionCreate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Create a new section within a course.
    Accessible only by the course's Instructor owner or an Admin.
    """
    section = await course_service.create_section(course_id, section_data, current_user)
    return section

@router.put("/{course_id}/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    course_id: str,
    section_id: str,
    update_data: SectionUpdate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Update details of a section.
    Accessible only by the course's Instructor owner or an Admin.
    """
    section = await course_service.update_section(course_id, section_id, update_data, current_user)
    return section

@router.delete("/{course_id}/sections/{section_id}", status_code=status.HTTP_200_OK)
async def delete_section(
    course_id: str,
    section_id: str,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Delete a section and all its lessons.
    Accessible only by the course's Instructor owner or an Admin.
    """
    response = await course_service.delete_section(course_id, section_id, current_user)
    return response

# ==================== LESSON ENDPOINTS ====================

@router.post("/{course_id}/sections/{section_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    course_id: str,
    section_id: str,
    lesson_data: LessonCreate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Create a new lesson within a section.
    Accessible only by the course's Instructor owner or an Admin.
    """
    lesson = await course_service.create_lesson(course_id, section_id, lesson_data, current_user)
    return lesson

@router.put("/{course_id}/sections/{section_id}/lessons/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    course_id: str,
    section_id: str,
    lesson_id: str,
    update_data: LessonUpdate,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Update details of a lesson.
    Accessible only by the course's Instructor owner or an Admin.
    """
    lesson = await course_service.update_lesson(course_id, section_id, lesson_id, update_data, current_user)
    return lesson

@router.delete("/{course_id}/sections/{section_id}/lessons/{lesson_id}", status_code=status.HTTP_200_OK)
async def delete_lesson(
    course_id: str,
    section_id: str,
    lesson_id: str,
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Delete a lesson.
    Accessible only by the course's Instructor owner or an Admin.
    """
    response = await course_service.delete_lesson(course_id, section_id, lesson_id, current_user)
    return response

@router.post("/{course_id}/sections/{section_id}/lessons/{lesson_id}/upload-video", response_model=LessonResponse)
async def upload_lesson_video(
    course_id: str,
    section_id: str,
    lesson_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(RoleChecker([UserRole.INSTRUCTOR, UserRole.ADMIN]))
):
    """
    Upload a lesson video file and save it locally.
    Updates the lesson's video URL.
    Accessible only by the course's Instructor owner or an Admin.
    """
    # Verify ownership
    await course_service.verify_course_owner_or_admin(course_id, current_user)
    
    # Check mime type
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video uploads are allowed for lessons")
        
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"video_{lesson_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    video_url = f"/static/uploads/{unique_filename}"
    
    lessons_coll = get_lessons_collection()
    from datetime import datetime, timezone
    await lessons_coll.update_one(
        {
            "_id": to_object_id(lesson_id),
            "section_id": to_object_id(section_id),
            "course_id": to_object_id(course_id)
        },
        {"$set": {"video_url": video_url, "updated_at": datetime.now(timezone.utc)}}
    )
    
    lesson_bson = await lessons_coll.find_one({"_id": to_object_id(lesson_id)})
    return bson_to_dict(lesson_bson)
