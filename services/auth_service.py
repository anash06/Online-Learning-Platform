import random
import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from bson import ObjectId

from database.mongodb import get_users_collection
from utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from utils.db_helpers import bson_to_dict
from schemas.user import UserCreate, UserLogin, ResetPasswordRequest

logger = logging.getLogger(__name__)

async def signup_user(user_data: UserCreate) -> dict:
    """Register a new user in the database."""
    users_collection = get_users_collection()
    
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
        
    hashed_pwd = hash_password(user_data.password)
    now = datetime.now(timezone.utc)
    
    user_doc = {
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_pwd,
        "role": user_data.role.value,
        "profile_picture": None,
        "bio": None,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "reset_otp": None,
        "reset_otp_expiry": None
    }
    
    result = await users_collection.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    return bson_to_dict(user_doc)

async def login_user(login_data: UserLogin) -> dict:
    """Authenticate user credentials and return access & refresh tokens."""
    users_collection = get_users_collection()
    
    user_bson = await users_collection.find_one({"email": login_data.email})
    if not user_bson:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    if not verify_password(login_data.password, user_bson["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    if not user_bson.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated"
        )
        
    user_dict = bson_to_dict(user_bson)
    user_id_str = user_dict["id"]
    
    # Create tokens
    token_data = {"sub": user_id_str, "role": user_dict["role"]}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_dict
    }

async def refresh_user_token(refresh_token: str) -> dict:
    """Validate refresh token and issue a new access/refresh token pair."""
    try:
        payload = decode_token(refresh_token, is_refresh=True)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    users_collection = get_users_collection()
    user_bson = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user_bson or not user_bson.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found"
        )
        
    user_dict = bson_to_dict(user_bson)
    token_data = {"sub": user_dict["id"], "role": user_dict["role"]}
    new_access = create_access_token(data=token_data)
    new_refresh = create_refresh_token(data=token_data)
    
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "user": user_dict
    }

async def request_password_reset(email: str) -> dict:
    """Simulate generating and sending a 6-digit OTP for password reset."""
    users_collection = get_users_collection()
    user_bson = await users_collection.find_one({"email": email})
    
    if not user_bson:
        # Avoid user enumeration attacks: return success but don't perform actions.
        # In this project, let's keep it clear for developers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found"
        )
        
    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Store in database
    await users_collection.update_one(
        {"_id": user_bson["_id"]},
        {"$set": {"reset_otp": otp, "reset_otp_expiry": expiry}}
    )
    
    # Simulate sending email by logging in a beautiful block
    logger.warning("\n" + "="*50 + f"\n[SIMULATED EMAIL] OTP SENT TO {email}\nOTP CODE: {otp}\nExpires at: {expiry}\n" + "="*50)
    
    return {
        "message": "A password reset OTP has been sent to your email",
        "simulated_otp_for_dev": otp  # Included in development responses for quick Swagger testing!
    }

async def reset_password_with_otp(reset_data: ResetPasswordRequest) -> dict:
    """Verify OTP and update the user's password."""
    users_collection = get_users_collection()
    user_bson = await users_collection.find_one({"email": reset_data.email})
    
    if not user_bson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    stored_otp = user_bson.get("reset_otp")
    otp_expiry = user_bson.get("reset_otp_expiry")
    
    if not stored_otp or stored_otp != reset_data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
        
    # Convert naive datetimes to timezone-aware if needed
    if otp_expiry:
        if otp_expiry.tzinfo is None:
            otp_expiry = otp_expiry.replace(tzinfo=timezone.utc)
            
    if datetime.now(timezone.utc) > otp_expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired"
        )
        
    # Hash new password
    hashed_pwd = hash_password(reset_data.new_password)
    
    # Reset columns
    await users_collection.update_one(
        {"_id": user_bson["_id"]},
        {"$set": {
            "hashed_password": hashed_pwd,
            "reset_otp": None,
            "reset_otp_expiry": None,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"message": "Password has been successfully updated"}
