"""Jobs router — filtered, paginated job listings."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.job import Job
from app.schemas.job import JobResponse

from sqlalchemy import func, select

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


@router.get("", response_model=dict)
async def list_jobs(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: float | None = Query(None),
    country: str | None = Query(None),
    sponsorship: str | None = Query(None),
    company: str | None = Query(None),
    search: str | None = Query(None),
) -> dict:
    """Get filtered, paginated, scored job listings."""
    threshold = min_score if min_score is not None else settings.MATCH_SCORE_THRESHOLD

    query = (
        select(Job)
        .where(Job.user_id == user.id)
        .order_by(Job.match_score.desc().nullslast(), Job.fetched_at.desc())
    )

    # Only show scored jobs above threshold (unless min_score=0 explicitly)
    if min_score != 0:
        query = query.where(
            (Job.match_score >= threshold) | (Job.match_score.is_(None))
        )

    if country:
        query = query.where(Job.country == country)
    if sponsorship:
        query = query.where(Job.sponsorship == sponsorship)
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if search:
        query = query.where(Job.title.ilike(f"%{search}%"))

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            JobResponse(
                id=str(j.id),
                title=j.title,
                company=j.company,
                location=j.location,
                country=j.country,
                url=j.url,
                match_score=j.match_score,
                match_rationale=j.match_rationale,
                sponsorship=j.sponsorship.value,
                fetched_at=j.fetched_at.isoformat(),
            ).model_dump()
            for j in jobs
        ],
    }
