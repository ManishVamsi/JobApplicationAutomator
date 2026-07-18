"""Admin router — external cron trigger endpoints.

These replace Celery beat schedules with simple HTTP endpoints that an
external cron service (e.g., cron-job.org, UptimeRobot, GitHub Actions
scheduled workflow) can call.

Auth: ADMIN_TRIGGER_SECRET in the Authorization header (Bearer <secret>).
The secret is NOT a JWT — it's a static hex token checked via constant-time
comparison. It must NOT be sent as a query parameter (query params get
logged in access logs and external cron dashboards).
"""

import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_redis
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)
settings = get_settings()


def verify_admin_secret(request: Request) -> None:
    """Dependency: verify the ADMIN_TRIGGER_SECRET from the Authorization header.

    Uses constant-time comparison to prevent timing attacks.
    Rejects requests if the secret is not configured (empty string).
    """
    if not settings.ADMIN_TRIGGER_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoints are disabled (ADMIN_TRIGGER_SECRET not configured)",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    provided = auth_header[7:]
    if not hmac.compare_digest(provided, settings.ADMIN_TRIGGER_SECRET):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin secret",
        )


@router.post(
    "/trigger-job-fetch",
    dependencies=[Depends(verify_admin_secret)],
)
async def trigger_job_fetch() -> dict:
    """Trigger the daily job fetch cycle for all users.

    Replaces Celery beat's daily schedule. Call this from an external cron
    (e.g., cron-job.org hitting POST /api/v1/admin/trigger-job-fetch).

    The fetch + scoring runs inline (awaited), so the cron caller gets a
    200 on success with a summary of what happened.
    """
    from app.services.background_tasks import run_fetch_jobs_for_all_users

    logger.info("Admin-triggered job fetch starting")
    result = await run_fetch_jobs_for_all_users()
    logger.info("Admin-triggered job fetch completed", **result)
    return result


@router.post(
    "/reset-jsearch-quota",
    dependencies=[Depends(verify_admin_secret)],
)
async def reset_jsearch_quota(
    redis=Depends(get_redis),  # noqa: ANN001
) -> dict:
    """Reset the JSearch monthly usage counter to 0.

    Replaces Celery beat's monthly cron (0 0 1 * *). Call this from an
    external cron on the 1st of each month.
    """
    await redis.set("jsearch:monthly_usage", 0)
    logger.info("JSearch monthly quota reset via admin endpoint")
    return {"status": "ok", "message": "JSearch monthly quota reset to 0"}
