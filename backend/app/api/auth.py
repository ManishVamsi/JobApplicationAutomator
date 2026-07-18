"""Auth router — OTP login, token refresh, logout.

All cookie flags are environment-conditional:
- Local dev (HTTP):  SameSite=Lax, Secure=False
- Production (HTTPS): SameSite=None, Secure=True
"""

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from jwt.exceptions import InvalidTokenError

from app.api.deps import DbSession, Limiter, Redis
from app.core.config import Environment, get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_otp,
    verify_csrf_access_token,
)
from app.models.user import User
from app.schemas.auth import MessageResponse, OTPRequest, OTPVerify, TokenResponse
from app.services.email_service import get_email_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

# OTP Redis key prefixes
OTP_KEY_PREFIX = "otp:"
OTP_ATTEMPTS_KEY_PREFIX = "otp_attempts:"
REFRESH_TOKEN_KEY_PREFIX = "refresh:"


def _get_cookie_flags() -> dict:
    """Return cookie flags based on ENVIRONMENT config.

    Local dev (HTTP): SameSite=Lax, Secure=False — cookies work over http://localhost.
    Production (HTTPS): SameSite=None, Secure=True — required for cross-domain delivery.
    """
    if settings.ENVIRONMENT == Environment.LOCAL:
        return {
            "httponly": True,
            "secure": False,
            "samesite": "lax",
            "path": REFRESH_COOKIE_PATH,
        }
    return {
        "httponly": True,
        "secure": True,
        "samesite": "none",
        "path": REFRESH_COOKIE_PATH,
    }


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token as an httpOnly cookie with env-conditional flags."""
    flags = _get_cookie_flags()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **flags,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    flags = _get_cookie_flags()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        **{k: v for k, v in flags.items() if k != "max_age"},
    )


@router.post("/request-otp", response_model=MessageResponse)
async def request_otp(
    body: OTPRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    redis: Redis,
    limiter: Limiter,
) -> MessageResponse:
    """Generate and send a 6-digit OTP to the user's email.

    Rate limited: 5/min per email.
    """
    # Rate limit by email
    allowed, _ = await limiter.check(
        f"ratelimit:otp_request:{body.email}",
        settings.RATE_LIMIT_OTP_REQUEST,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Try again in a minute.",
        )

    code = generate_otp()

    # Store OTP in Redis with TTL
    otp_key = f"{OTP_KEY_PREFIX}{body.email}"
    await redis.setex(otp_key, settings.OTP_EXPIRE_MINUTES * 60, code)

    # Reset attempt counter for this OTP
    attempts_key = f"{OTP_ATTEMPTS_KEY_PREFIX}{body.email}"
    await redis.delete(attempts_key)

    # Send OTP via email (ConsoleEmailService for local dev, ResendEmailService for prod)
    email_service = get_email_service()
    background_tasks.add_task(email_service.send_otp, body.email, code)

    return MessageResponse(message="OTP sent to your email")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerify,
    request: Request,
    response: Response,
    db: DbSession,
    redis: Redis,
    limiter: Limiter,
) -> TokenResponse:
    """Verify the OTP and issue JWT access + refresh tokens.

    Brute-force protected:
    - Per-IP rate limit: 10/min
    - Per-OTP attempt counter: 5 failures → OTP invalidated
    """
    # Per-IP rate limit on verify-otp
    client_ip = request.client.host if request.client else "unknown"
    allowed, _ = await limiter.check(
        f"ratelimit:otp_verify:{client_ip}",
        settings.RATE_LIMIT_OTP_VERIFY,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Try again in a minute.",
        )

    otp_key = f"{OTP_KEY_PREFIX}{body.email}"
    attempts_key = f"{OTP_ATTEMPTS_KEY_PREFIX}{body.email}"

    # Check if OTP exists
    stored_code = await redis.get(otp_key)
    if stored_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired or not requested. Please request a new code.",
        )

    # Check attempt count
    attempts = await redis.get(attempts_key)
    attempt_count = int(attempts) if attempts else 0

    if attempt_count >= settings.OTP_MAX_ATTEMPTS:
        # Invalidate the OTP — force re-request
        await redis.delete(otp_key)
        await redis.delete(attempts_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please request a new code.",
        )

    # Verify the code
    if stored_code != body.code:
        # Increment attempts
        pipe = redis.pipeline()
        pipe.incr(attempts_key)
        pipe.expire(attempts_key, settings.OTP_EXPIRE_MINUTES * 60)
        await pipe.execute()

        remaining = settings.OTP_MAX_ATTEMPTS - attempt_count - 1
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OTP. {remaining} attempts remaining.",
        )

    # OTP verified — clean up
    await redis.delete(otp_key)
    await redis.delete(attempts_key)

    # Find or create user
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=body.email, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
        db.add(user)
        await db.flush()

    user_id = str(user.id)

    # Create tokens
    access_token = create_access_token(user_id)
    refresh_token, jti = create_refresh_token(user_id)

    # Store refresh JTI in Redis allowlist
    refresh_key = f"{REFRESH_TOKEN_KEY_PREFIX}{user_id}:{jti}"
    await redis.setex(refresh_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")

    # Set refresh cookie
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    redis: Redis,
) -> TokenResponse:
    """Issue a new access token using the refresh cookie.

    CSRF-protected: requires the (possibly expired) access token in the
    Authorization header as proof of recent possession.
    Validates: signature, sub match, and staleness ceiling (default 48h).
    """
    # Get refresh token from cookie
    refresh_cookie = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token cookie",
        )

    # Decode refresh token (enforces type == "refresh")
    try:
        refresh_payload = decode_refresh_token(refresh_cookie)
    except InvalidTokenError as e:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        )

    user_id = refresh_payload["sub"]
    jti = refresh_payload.get("jti")

    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing JTI",
        )

    # Check JTI is in Redis allowlist
    refresh_key = f"{REFRESH_TOKEN_KEY_PREFIX}{user_id}:{jti}"
    exists = await redis.exists(refresh_key)
    if not exists:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked or expired",
        )

    # CSRF proof: require access token in Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CSRF proof required: include access token in Authorization header",
        )

    csrf_token = auth_header[7:]
    try:
        verify_csrf_access_token(
            csrf_token,
            expected_user_id=user_id,
            max_age_hours=settings.CSRF_MAX_TOKEN_AGE_HOURS,
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"CSRF proof failed: {e}",
        )

    # Revoke old refresh token (rotation)
    await redis.delete(refresh_key)

    # Issue new tokens
    access_token = create_access_token(user_id)
    new_refresh_token, new_jti = create_refresh_token(user_id)

    # Store new refresh JTI
    new_refresh_key = f"{REFRESH_TOKEN_KEY_PREFIX}{user_id}:{new_jti}"
    await redis.setex(new_refresh_key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")

    # Set new refresh cookie
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    redis: Redis,
) -> None:
    """Revoke the refresh token and clear the cookie."""
    refresh_cookie = request.cookies.get(REFRESH_COOKIE_NAME)

    if refresh_cookie:
        try:
            payload = decode_refresh_token(refresh_cookie)
            user_id = payload["sub"]
            jti = payload.get("jti")
            if jti:
                refresh_key = f"{REFRESH_TOKEN_KEY_PREFIX}{user_id}:{jti}"
                await redis.delete(refresh_key)
        except InvalidTokenError:
            pass  # Token already invalid — still clear the cookie

    _clear_refresh_cookie(response)
