"""FastAPI dependency injection — database sessions, auth, and rate limiting."""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.middleware import RateLimiter
from app.core.security import decode_access_token, hash_api_token
from app.models.user import User

settings = get_settings()

# --- HTTP Bearer scheme ---
bearer_scheme = HTTPBearer(auto_error=False)

# --- Redis client (singleton via dependency) ---
_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get the shared async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


async def get_rate_limiter(
    redis: aioredis.Redis = Depends(get_redis),
) -> RateLimiter:
    """Get a rate limiter backed by the shared Redis client."""
    return RateLimiter(redis)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Decode the JWT access token and return the authenticated user.

    Enforces type == "access" — refresh tokens are rejected with 401.
    This is the primary protection against JWT token confusion attacks.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim",
        )

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_from_api_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via the long-lived extension API token (Bearer jaa_...).

    Used by the LinkedIn post ingestion endpoint — not the JWT access token.
    Looks up the token's SHA-256 hash in ApiToken, resolves user_id.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API token",
        )

    raw_token = auth_header[7:]  # Strip "Bearer "
    if not raw_token.startswith("jaa_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token format",
        )

    token_hash_value = hash_api_token(raw_token)

    from sqlalchemy import select

    from app.models.api_token import ApiToken

    result = await db.execute(
        select(ApiToken).where(
            ApiToken.token_hash == token_hash_value,
            ApiToken.revoked_at.is_(None),
        )
    )
    api_token = result.scalar_one_or_none()

    if api_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API token",
        )

    # Update last_used_at
    from datetime import UTC, datetime

    api_token.last_used_at = datetime.now(UTC)

    # Load the user
    result = await db.execute(select(User).where(User.id == api_token.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for API token",
        )

    return user


# Type aliases for cleaner router signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[aioredis.Redis, Depends(get_redis)]
Limiter = Annotated[RateLimiter, Depends(get_rate_limiter)]
