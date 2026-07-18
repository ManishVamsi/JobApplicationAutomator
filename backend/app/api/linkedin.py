"""LinkedIn posts router — ingestion (API token auth), query, manual add."""

from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    DbSession,
    Limiter,
    Redis,
    get_current_user_from_api_token,
    get_db,
    get_rate_limiter,
    get_redis,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.linkedin_post import PostSource
from app.models.user import User
from app.schemas.linkedin_post import LinkedInPostIngest, LinkedInPostResponse
from app.services.linkedin_post_service import LinkedInPostService

router = APIRouter(prefix="/linkedin-posts", tags=["linkedin"])
logger = get_logger(__name__)
settings = get_settings()

linkedin_service = LinkedInPostService()


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_post(
    body: LinkedInPostIngest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_from_api_token),
    db: AsyncSession = Depends(get_db),
    redis: object = Depends(get_redis),
    limiter: object = Depends(get_rate_limiter),
) -> dict:
    """Ingest a LinkedIn post from the browser extension.

    Authenticates via the extension API token (Bearer jaa_...), not JWT.
    Per-user rate limited: 30/min (separate from IP-based general limit).
    """
    user_id = str(user.id)

    # Per-user rate limit (30/min keyed by user_id)
    allowed, _ = await limiter.check(  # type: ignore[union-attr]
        f"ratelimit:linkedin_ingest:{user_id}",
        settings.RATE_LIMIT_LINKEDIN_INGEST,
    )
    if not allowed:
        # Log to AuditLog — repeated hits signal compromised token or malfunction
        audit_entry = AuditLog(
            user_id=user.id,
            action="linkedin_ingest_rate_limited",
            target_type="linkedin_post",
            metadata_={"ip": request.client.host if request.client else None},
            created_at=datetime.now(UTC),
        )
        db.add(audit_entry)
        await db.commit()

        logger.warning(
            "LinkedIn ingest rate limit exceeded",
            user_id=user_id,
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 30 posts per minute.",
        )

    post = await linkedin_service.ingest_post(
        db,
        user_id,
        body.post_url,
        body.raw_text,
        body.poster_name,
        PostSource.EXTENSION,
    )

    if post is None:
        return {"message": "Duplicate post — already ingested.", "duplicate": True}

    # Dispatch scoring as a background task
    from app.services.background_tasks import run_score_linkedin_posts

    background_tasks.add_task(run_score_linkedin_posts, user_id)

    return {
        "id": str(post.id),
        "message": "Post ingested. Scoring will complete in the background.",
    }


@router.get("", response_model=dict)
async def list_posts(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: float | None = Query(None),
    country: str | None = Query(None),
    sponsorship: str | None = Query(None),
) -> dict:
    """Get scored LinkedIn posts above the threshold, filtered and paginated."""
    posts, total = await linkedin_service.get_scored_posts(
        db,
        str(user.id),
        page=page,
        page_size=page_size,
        min_score=min_score,
        country=country,
        sponsorship=sponsorship,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            LinkedInPostResponse(
                id=str(p.id),
                post_url=p.post_url,
                poster_name=p.poster_name,
                raw_text=p.raw_text[:500],
                match_score=p.match_score,
                match_rationale=p.match_rationale,
                country=p.country,
                sponsorship=p.sponsorship.value,
                source=p.source.value,
                submitted_at=p.submitted_at.isoformat(),
                scored_at=p.scored_at.isoformat() if p.scored_at else None,
            ).model_dump()
            for p in posts
        ],
    }


@router.post("/manual", status_code=status.HTTP_201_CREATED)
async def manual_add(
    body: LinkedInPostIngest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Manually add a LinkedIn post (paste URL + text)."""
    post = await linkedin_service.ingest_post(
        db,
        str(user.id),
        body.post_url,
        body.raw_text,
        body.poster_name,
        PostSource.MANUAL,
    )

    if post is None:
        return {"message": "Duplicate post.", "duplicate": True}

    # Dispatch scoring as a background task
    from app.services.background_tasks import run_score_linkedin_posts

    background_tasks.add_task(run_score_linkedin_posts, str(user.id))

    return {
        "id": str(post.id),
        "message": "Post added. Scoring will complete in the background.",
    }
