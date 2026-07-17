"""JSearch job fetch service — daily fetch with quota tracking."""

import hashlib
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.job import Job, SponsorshipStatus
from app.models.user import User

logger = get_logger(__name__)
settings = get_settings()

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"


class JobFetchService:
    """Fetches jobs from JSearch API with strict quota management.

    Budget: JSEARCH_MONTHLY_LIMIT (default 200) requests/month.
    Per cycle: JSEARCH_PER_CYCLE_CAP (default 6) requests max.
    Cadence: once daily (driven by Celery beat).
    """

    async def fetch_for_user(
        self,
        db: AsyncSession,
        redis: object,  # aioredis.Redis
        user: User,
    ) -> int:
        """Fetch jobs for a single user based on their target roles/locations.

        Returns the number of new jobs stored.
        """
        if not user.target_roles:
            logger.info("User has no target roles, skipping", user_id=str(user.id))
            return 0

        new_jobs_count = 0
        requests_made = 0

        for role in user.target_roles[:3]:  # Limit roles to conserve quota
            if requests_made >= settings.JSEARCH_PER_CYCLE_CAP:
                break

            # Check monthly quota
            monthly_used = int(await redis.get("jsearch:monthly_usage") or 0)  # type: ignore[union-attr]
            if monthly_used >= settings.JSEARCH_MONTHLY_LIMIT:
                logger.warning(
                    "JSearch monthly quota exhausted",
                    used=monthly_used,
                    limit=settings.JSEARCH_MONTHLY_LIMIT,
                )
                break

            locations = user.target_locations or [""]
            for location in locations[:2]:  # Limit locations per role
                if requests_made >= settings.JSEARCH_PER_CYCLE_CAP:
                    break

                query = f"{role} {location}".strip()
                try:
                    jobs_data = await self._search_jsearch(query)
                    requests_made += 1

                    # Track usage in Redis
                    await redis.incr("jsearch:monthly_usage")  # type: ignore[union-attr]

                    for job_data in jobs_data:
                        stored = await self._store_job(db, user, job_data)
                        if stored:
                            new_jobs_count += 1

                except httpx.HTTPError as e:
                    logger.error("JSearch API error", error=str(e), query=query)
                    continue

        # Update last fetch timestamp
        await redis.set("jsearch:last_fetch_at", datetime.now(UTC).isoformat())  # type: ignore[union-attr]

        logger.info(
            "Job fetch completed",
            user_id=str(user.id),
            new_jobs=new_jobs_count,
            requests_made=requests_made,
        )
        return new_jobs_count

    async def _search_jsearch(self, query: str) -> list[dict]:
        """Call JSearch API and return job listing data."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                JSEARCH_API_URL,
                params={
                    "query": query,
                    "page": "1",
                    "num_pages": "1",
                },
                headers={
                    "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def _store_job(
        self, db: AsyncSession, user: User, job_data: dict
    ) -> bool:
        """Store a job if it doesn't already exist (dedup by external_id per user)."""
        external_id = job_data.get("job_id", "")
        if not external_id:
            return False

        # Check for existing
        result = await db.execute(
            select(Job).where(
                Job.user_id == user.id,
                Job.external_id == external_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return False  # Already exists

        description = job_data.get("job_description", "")
        description_hash = hashlib.sha256(description.encode()).hexdigest() if description else None

        job = Job(
            user_id=user.id,
            external_id=external_id,
            title=job_data.get("job_title", "Unknown"),
            company=job_data.get("employer_name"),
            location=job_data.get("job_city", ""),
            country=job_data.get("job_country"),
            posted_date=None,  # Parsed from job_data if available
            description_hash=description_hash,
            url=job_data.get("job_apply_link"),
            sponsorship=SponsorshipStatus.UNKNOWN,
            raw_data=job_data,
            fetched_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(job)
        return True
