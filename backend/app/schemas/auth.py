"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr


class OTPRequest(BaseModel):
    """Request body for POST /auth/request-otp."""

    email: EmailStr


class OTPVerify(BaseModel):
    """Request body for POST /auth/verify-otp."""

    email: EmailStr
    code: str


class TokenResponse(BaseModel):
    """Response body containing the access token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
