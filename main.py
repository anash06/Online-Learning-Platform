from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import os

from config.config import settings
from database.mongodb import connect_to_mongo, close_mongo_connection, get_categories_collection
from middleware.rate_limit import RateLimiterMiddleware

# Configure logging formats
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ==================== DATABASE SEEDING ====================

async def seed_initial_categories():
    """Seed default categories into MongoDB on platform startup if empty."""
    try:
        categories_coll = get_categories_collection()
        count = await categories_coll.count_documents({})
        if count == 0:
            logger.info("Database empty of categories. Seeding default list...")
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            default_categories = [
                {"name": "Web Development", "description": "HTML, CSS, JavaScript, React, Node.js, FastAPI & Fullstack Engineering"},
                {"name": "Data Science & AI", "description": "Python, Machine Learning, Deep Learning, Artificial Intelligence & Data Analytics"},
                {"name": "Mobile Development", "description": "Swift, Kotlin, React Native & Flutter mobile applications"},
                {"name": "Design & UI/UX", "description": "Figma, Adobe XD, User Experience & Visual Design methodologies"},
                {"name": "Business & Marketing", "description": "Digital Marketing, SEO, Finance, Management & Entrepreneurship"}
            ]
            for cat in default_categories:
                cat["created_at"] = now
                cat["updated_at"] = now
                
            await categories_coll.insert_many(default_categories)
            logger.info("Successfully seeded 5 default course categories.")
    except Exception as e:
        logger.error(f"Error seeding initial categories: {e}")

# ==================== LIFESPAN SYSTEM ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up FastAPI application...")
    
    # 1. Initialize MongoDB connection
    await connect_to_mongo()
    
    # 2. Seed initial categories
    await seed_initial_categories()
    
    # 3. Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    yield
    # Shutdown actions
    logger.info("Shutting down FastAPI application...")
    await close_mongo_connection()

# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title="Online Learning Platform Backend API",
    description="Production-Ready Asynchronous REST APIs for an e-Learning platform featuring MongoDB, JWT Authentication, and Razorpay Payments.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to allow only specific React frontends
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply Rate Limiting (120 requests per minute per IP)
app.add_middleware(RateLimiterMiddleware, requests_limit=120, window_seconds=60)

# Serve uploaded media files locally
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ==================== GLOBAL EXCEPTION HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Format HTTP exceptions into standardized API responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic schema validation errors into readable lists."""
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join([str(loc) for loc in error["loc"][1:]]) or "body",
            "message": error["msg"]
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Input validation failed",
            "validation_errors": error_details
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Prevent application crashes and mask raw stack traces in production."""
    logger.error(f"Global unhandled exception on path {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error. Our engineering team has been notified."
        }
    )

# ==================== ROUTERS REGISTRATION ====================

from routers import (
    auth,
    user,
    course,
    payment,
    enrollment,
    review,
    wishlist,
    instructor,
    admin
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(course.router, prefix="/api/v1")
app.include_router(payment.router, prefix="/api/v1")
app.include_router(enrollment.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(wishlist.router, prefix="/api/v1")
app.include_router(instructor.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")

# ==================== ROOT REDIRECT ====================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect landing root requests to interactive Swagger APIs documentation."""
    return RedirectResponse(url="/docs")
