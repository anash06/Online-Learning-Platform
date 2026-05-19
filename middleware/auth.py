from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
import logging

from utils.security import decode_token
from database.mongodb import get_users_collection
from utils.db_helpers import bson_to_dict
from schemas.user import UserRole
from bson import ObjectId

logger = logging.getLogger(__name__)
security_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> dict:
    """
    FastAPI dependency to extract and validate the JWT from the Authorization header.
    Returns the authenticated user document as a dict.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token, is_refresh=False)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception as e:
        logger.error(f"JWT verification failed: {e}")
        raise credentials_exception
        
    users_collection = get_users_collection()
    try:
        user_bson = await users_collection.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise credentials_exception
        
    if user_bson is None:
        raise credentials_exception
        
    user_dict = bson_to_dict(user_bson)
    if not user_dict.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
        
    return user_dict

class RoleChecker:
    """Dependency checker to enforce role-based access control on endpoints."""
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of these roles: {[r.value for r in self.allowed_roles]}"
            )
        return current_user
