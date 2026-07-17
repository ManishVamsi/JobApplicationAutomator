"""Health check endpoint — service status + quota metrics."""

from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.api.deps import Redis
from app.core.config import get_settings
from app.core.database import engine

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def healthz(redis: Redis) -> dict:
    """Health check with service status and quota metrics.

    Returns:
        - Service status (database, redis, celery)
        - JSearch quota usage vs limit
        - Groq daily usage
        - Last successful job fetch timestamp
    """
    health: dict = {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {e}"
        health["status"] = "degraded"

    # Redis check
    try:
        await redis.ping()
        health["redis"] = "connected"
    except Exception as e:
        health["redis"] = f"error: {e}"
        health["status"] = "degraded"

    # JSearch quota
    try:
        monthly_used = await redis.get("jsearch:monthly_usage") or "0"
        reset_day = await redis.get("jsearch:quota_reset_date")
        health["jsearch_quota"] = {
            "used": int(monthly_used),
            "limit": settings.JSEARCH_MONTHLY_LIMIT,
            "remaining": max(0, settings.JSEARCH_MONTHLY_LIMIT - int(monthly_used)),
            "resets_on": reset_day or "unknown",
        }
    except Exception:
        health["jsearch_quota"] = None

    # Last job fetch
    try:
        last_fetch = await redis.get("jsearch:last_fetch_at")
        health["last_job_fetch"] = last_fetch
    except Exception:
        health["last_job_fetch"] = None

    # Groq daily usage
    try:
        groq_used = await redis.get("groq:daily_usage") or "0"
        health["groq_usage"] = {
            "used_today": int(groq_used),
            "daily_limit": settings.GROQ_DAILY_LIMIT,
        }
    except Exception:
        health["groq_usage"] = None

    return health
