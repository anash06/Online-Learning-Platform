import razorpay
import logging
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from bson import ObjectId

from config.config import settings
from database.mongodb import (
    get_courses_collection,
    get_payments_collection,
    get_enrollments_collection,
    get_progress_collection
)
from utils.db_helpers import bson_to_dict, to_object_id
from schemas.payment import PaymentVerification

logger = logging.getLogger(__name__)

# Initialize Razorpay Client
try:
    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
except Exception as e:
    razorpay_client = None
    logger.error(f"Failed to initialize Razorpay client: {e}")

async def create_payment_order(course_id: str, student_id: str) -> dict:
    """Create a new payment order using Razorpay."""
    courses_coll = get_courses_collection()
    payments_coll = get_payments_collection()
    enrollments_coll = get_enrollments_collection()
    
    # 1. Fetch Course details
    course = await courses_coll.find_one({"_id": to_object_id(course_id)})
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
        
    if not course.get("is_published", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enroll in an unpublished course"
        )
        
    # 2. Check if already enrolled
    existing_enrollment = await enrollments_coll.find_one({
        "course_id": to_object_id(course_id),
        "student_id": to_object_id(student_id),
        "status": "active"
    })
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already enrolled in this course"
        )
        
    # 3. Handle free courses (immediately enroll)
    if course["price"] == 0:
        await enroll_student_in_course(student_id, course_id)
        # Return a custom message indicating instant free enrollment
        return {
            "message": "Free enrollment successful",
            "enrolled": True,
            "course_id": course_id
        }
        
    # 4. Create Razorpay order
    amount_in_paise = int(course["price"] * 100)
    currency = "INR"
    receipt_id = f"receipt_{uuid.uuid4().hex[:12]}"
    
    order_id = None
    is_mock = False
    
    # Check if keys are placeholders or clients fail
    if not razorpay_client or settings.RAZORPAY_KEY_ID == "rzp_test_samplekeyid12345":
        # Generate simulated order ID
        order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        is_mock = True
        logger.warning(f"Using simulated payment order due to default Razorpay API keys: {order_id}")
    else:
        try:
            data = {
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt_id,
                "payment_capture": 1
            }
            order = razorpay_client.order.create(data=data)
            order_id = order["id"]
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}. Falling back to simulation.")
            order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
            is_mock = True
            
    # 5. Save payment history in MongoDB as pending
    now = datetime.now(timezone.utc)
    payment_doc = {
        "order_id": order_id,
        "payment_id": None,
        "signature": None,
        "student_id": to_object_id(student_id),
        "course_id": to_object_id(course_id),
        "amount": course["price"],
        "currency": currency,
        "status": "pending",
        "is_mock": is_mock,
        "created_at": now,
        "updated_at": now
    }
    
    await payments_coll.insert_one(payment_doc)
    
    return {
        "order_id": order_id,
        "amount": course["price"],
        "currency": currency,
        "course_id": course_id,
        "key_id": settings.RAZORPAY_KEY_ID
    }

async def verify_payment_signature(verification_data: PaymentVerification, student_id: str) -> dict:
    """Verify the Razorpay payment signature and grant course access."""
    payments_coll = get_payments_collection()
    
    # 1. Fetch pending payment record
    payment_record = await payments_coll.find_one({
        "order_id": verification_data.razorpay_order_id,
        "student_id": to_object_id(student_id)
    })
    
    if not payment_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment order record not found"
        )
        
    if payment_record["status"] == "success":
        return {"message": "Payment already processed and verified", "status": "success"}
        
    # 2. Cryptographic signature check
    is_verified = False
    
    if payment_record.get("is_mock", False) or settings.RAZORPAY_KEY_ID == "rzp_test_samplekeyid12345":
        # Dev fallback: Simulated validation passes
        is_verified = True
        logger.warning(f"Payment verified through simulated mock signature for: {verification_data.razorpay_order_id}")
    else:
        try:
            params_dict = {
                'razorpay_order_id': verification_data.razorpay_order_id,
                'razorpay_payment_id': verification_data.razorpay_payment_id,
                'razorpay_signature': verification_data.razorpay_signature
            }
            # Verify signature using the SDK (raises SignatureVerificationError if invalid)
            razorpay_client.utility.verify_payment_signature(params_dict)
            is_verified = True
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {e}")
            is_verified = False
            
    now = datetime.now(timezone.utc)
    
    if is_verified:
        # 3. Update payment record to success
        await payments_coll.update_one(
            {"_id": payment_record["_id"]},
            {
                "$set": {
                    "payment_id": verification_data.razorpay_payment_id,
                    "signature": verification_data.razorpay_signature,
                    "status": "success",
                    "updated_at": now
                }
            }
        )
        
        # 4. Enroll the student in the course
        await enroll_student_in_course(student_id, str(payment_record["course_id"]))
        
        return {"message": "Payment verified and course access granted successfully", "status": "success"}
    else:
        # Update payment record to failed
        await payments_coll.update_one(
            {"_id": payment_record["_id"]},
            {
                "$set": {
                    "status": "failed",
                    "updated_at": now
                }
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed. Cryptographic signature is invalid."
        )

# ==================== HELPER ENROLLMENT TRIGGERS ====================

async def enroll_student_in_course(student_id: str, course_id: str):
    """Internal business logic helper to register student enrollments and progress structures."""
    enrollments_coll = get_enrollments_collection()
    courses_coll = get_courses_collection()
    progress_coll = get_progress_collection()
    
    now = datetime.now(timezone.utc)
    
    # 1. Double check enrollment doesn't exist
    existing = await enrollments_coll.find_one({
        "student_id": to_object_id(student_id),
        "course_id": to_object_id(course_id)
    })
    
    if existing:
        if existing["status"] == "active":
            return
        else:
            # Reactivate previously refunded/cancelled enrollment
            await enrollments_coll.update_one(
                {"_id": existing["_id"]},
                {"$set": {"status": "active", "enrolled_at": now, "progress_percentage": 0.0}}
            )
    else:
        # Create new enrollment
        enrollment_doc = {
            "student_id": to_object_id(student_id),
            "course_id": to_object_id(course_id),
            "enrolled_at": now,
            "progress_percentage": 0.0,
            "status": "active"
        }
        await enrollments_coll.insert_one(enrollment_doc)
        
    # 2. Increment enrollment count on course document
    await courses_coll.update_one(
        {"_id": to_object_id(course_id)},
        {"$inc": {"enrollment_count": 1}}
    )
    
    # 3. Initialize progress tracker
    await progress_coll.update_one(
        {
            "student_id": to_object_id(student_id),
            "course_id": to_object_id(course_id)
        },
        {
            "$setOnInsert": {
                "student_id": to_object_id(student_id),
                "course_id": to_object_id(course_id),
                "completed_lessons": [],
                "updated_at": now
            }
        },
        upsert=True
    )
