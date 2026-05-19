from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PaymentOrderCreate(BaseModel):
    course_id: str

class PaymentOrderResponse(BaseModel):
    order_id: str
    amount: float
    currency: str = "INR"
    course_id: str
    key_id: str  # Razorpay public key ID so the frontend knows what key to use

class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    course_id: str

class PaymentResponse(BaseModel):
    id: str
    student_id: str
    course_id: str
    course_title: Optional[str] = None
    amount: float
    currency: str
    status: str  # pending, success, failed
    created_at: datetime

    class Config:
        from_attributes = True
