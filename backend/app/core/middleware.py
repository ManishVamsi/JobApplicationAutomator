"""CORS and rate limiting middleware."""

from __future__ import annotations

import time
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_cors(app: FastAPI) -> None:
    """Configure CORS for cross-domain frontend/backend deployment.

    - allow_origins: exact FRONTEND_URL only — never a wildcard, which
      browsers reject when credentials=True.
    - allow_credentials: True — required for httpOnly refresh cookie
      to be sent cross-origin.
    """
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


class RateLimiter:
    """Redis-based sliding window rate limiter.

    Reusable across auth endpoints, LinkedIn ingest, and general middleware.
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if a request is within the rate limit.

        Args:
            key: The rate limit key (e.g., "ratelimit:otp_request:{email}").
            limit: Maximum requests allowed in the window.
            window_seconds: Sliding window duration in seconds.

        Returns:
            Tuple of (allowed: bool, info: dict with remaining, limit, reset_at).
        """
        now = time.time()
        window_start = now - window_seconds
        pipe = self._redis.pipeline()

        # Remove entries outside the window
        pipe.zremrangebyscore(key, 0, window_start)  # type: ignore[union-attr]
        # Count entries in the window
        pipe.zcard(key)  # type: ignore[union-attr]
        # Add current request
        pipe.zadd(key, {str(now): now})  # type: ignore[union-attr]
        # Set TTL on the key
        pipe.expire(key, window_seconds)  # type: ignore[union-attr]

        results = await pipe.execute()
        current_count: int = results[1]

        allowed = current_count < limit
        info = {
            "remaining": max(0, limit - current_count - 1) if allowed else 0,
            "limit": limit,
            "reset_at": int(now + window_seconds),
        }

        if not allowed:
            # Remove the entry we just added (request was denied)
            await self._redis.zrem(key, str(now))
            logger.warning(
                "Rate limit exceeded",
                key=key,
                limit=limit,
                window_seconds=window_seconds,
            )

        return allowed, info
