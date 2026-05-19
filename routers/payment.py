from fastapi import APIRouter, Depends, status
from schemas.payment import PaymentOrderCreate, PaymentOrderResponse, PaymentVerification
from middleware.auth import get_current_user, RoleChecker
from schemas.user import UserRole
from services import payment_service

router = APIRouter(prefix="/payments", tags=["Payment Integration"])

@router.post("/create-order", response_model=dict)
async def create_order(
    order_data: PaymentOrderCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new payment order using Razorpay.
    If the course is free (price = 0.0), it immediately enrolls the student!
    Accessible by all authenticated users.
    """
    response = await payment_service.create_payment_order(
        course_id=order_data.course_id,
        student_id=current_user["id"]
    )
    return response

@router.post("/verify-signature", status_code=status.HTTP_200_OK)
async def verify_signature(
    verification_data: PaymentVerification,
    current_user: dict = Depends(get_current_user)
):
    """
    Verify the Razorpay payment signature.
    If signature is valid, updates payment history status to success and grants course enrollment.
    """
    response = await payment_service.verify_payment_signature(
        verification_data=verification_data,
        student_id=current_user["id"]
    )
    return response
