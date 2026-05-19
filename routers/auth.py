from fastapi import APIRouter, Depends, status
from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """
    Register a new user (Student, Instructor, or Admin).
    Password is automatically and securely hashed.
    """
    user = await auth_service.signup_user(user_data)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """
    Authenticate user and retrieve access + refresh tokens.
    """
    tokens = await auth_service.login_user(login_data)
    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """
    Retrieve a new access + refresh token pair using a valid refresh token.
    """
    tokens = await auth_service.refresh_user_token(refresh_data.refresh_token)
    return tokens

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(forgot_data: ForgotPasswordRequest):
    """
    Request a simulated 6-digit OTP code for password reset.
    For development ease, the OTP code is logged in the console AND returned in the API payload.
    """
    response = await auth_service.request_password_reset(forgot_data.email)
    return response

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(reset_data: ResetPasswordRequest):
    """
    Verify the 6-digit OTP code and securely change the user's password.
    """
    response = await auth_service.reset_password_with_otp(reset_data)
    return response
