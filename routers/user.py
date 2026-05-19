from fastapi import APIRouter, Depends, status
from schemas.user import UserResponse, UserUpdate
from middleware.auth import get_current_user
from database.mongodb import get_users_collection
from utils.db_helpers import bson_to_dict, to_object_id
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve details of the currently authenticated user."""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update profile details of the currently authenticated user."""
    users_coll = get_users_collection()
    
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        return current_user
        
    update_dict["updated_at"] = datetime.now(timezone.utc)
    
    await users_coll.update_one(
        {"_id": to_object_id(current_user["id"])},
        {"$set": update_dict}
    )
    
    updated_user = await users_coll.find_one({"_id": to_object_id(current_user["id"])})
    return bson_to_dict(updated_user)
