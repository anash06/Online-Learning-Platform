from fastapi import APIRouter, Depends, status
from schemas.wishlist import WishlistToggle, WishlistResponse, WishlistDetailResponse
from middleware.auth import get_current_user
from services import student_service

router = APIRouter(prefix="/wishlist", tags=["Wishlist Module"])

@router.post("/toggle", response_model=WishlistResponse)
async def toggle_wishlist(
    data: WishlistToggle,
    current_user: dict = Depends(get_current_user)
):
    """
    Toggle a course in the student's wishlist.
    Adds the course if it is not present; removes it if it is.
    """
    wishlist = await student_service.toggle_wishlist_item(
        student_id=current_user["id"],
        course_id=data.course_id
    )
    return wishlist

@router.get("/", response_model=WishlistDetailResponse)
async def get_wishlist(current_user: dict = Depends(get_current_user)):
    """
    Fetch all items inside the student's wishlist with full course details populated.
    """
    wishlist = await student_service.get_wishlist_details(student_id=current_user["id"])
    return wishlist
