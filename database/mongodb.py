from motor.motor_asyncio import AsyncIOMotorClient
from config.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db_instance.db = db_instance.client[settings.DATABASE_NAME]
        # Verify connection by pinging
        await db_instance.client.admin.command('ping')
        logger.info("Connected to MongoDB successfully!")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db_instance.client:
        logger.info("Closing MongoDB connection...")
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    if db_instance.db is None:
        raise RuntimeError("Database not initialized. Ensure connect_to_mongo() has run.")
    return db_instance.db

# Helper getters for collections
def get_users_collection():
    return get_database()["users"]

def get_courses_collection():
    return get_database()["courses"]

def get_sections_collection():
    return get_database()["sections"]

def get_lessons_collection():
    return get_database()["lessons"]

def get_enrollments_collection():
    return get_database()["enrollments"]

def get_payments_collection():
    return get_database()["payments"]

def get_reviews_collection():
    return get_database()["reviews"]

def get_wishlist_collection():
    return get_database()["wishlist"]

def get_progress_collection():
    return get_database()["progress"]

def get_categories_collection():
    return get_database()["categories"]
