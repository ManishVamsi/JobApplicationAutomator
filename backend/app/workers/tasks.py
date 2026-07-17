"""Celery tasks for job fetching, scoring, and LinkedIn post scoring."""

import asyncio
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.score_jobs_for_user")
def score_jobs_for_user(user_id: str) -> dict:
    """Score unscored jobs for a user using the LLM matching service."""

    async def _score() -> dict:
        from sqlalchemy import select

        from app.core.config import get_settings
        from app.core.database import async_session_factory
        from app.models.job import Job
        from app.models.resume import Resume
        from app.services.groq_matching_service import GroqMatchingService
        from app.services.matching_service import JobData

        settings = get_settings()
        matching = GroqMatchingService()

        async with async_session_factory() as db:
            # Get user's parsed resume
            result = await db.execute(
                select(Resume).where(Resume.user_id == user_id)
            )
            resume = result.scalar_one_or_none()
            if not resume or not resume.parsed_data:
                return {"status": "skipped", "reason": "no parsed resume"}

            from app.services.matching_service import ResumeData

            resume_data = ResumeData(
                skills=resume.parsed_data.get("skills", []),
                experience=resume.parsed_data.get("experience", []),
                education=resume.parsed_data.get("education", []),
                roles=resume.parsed_data.get("roles", []),
                years_of_experience=resume.parsed_data.get("years_of_experience", 0),
                raw_text=resume.parsed_data.get("raw_text", ""),
            )

            # Get unscored jobs
            result = await db.execute(
                select(Job).where(Job.user_id == user_id, Job.match_score.is_(None))
            )
            unscored_jobs = list(result.scalars().all())

            if not unscored_jobs:
                return {"status": "skipped", "reason": "no unscored jobs"}

            job_data_list = [
                JobData(
                    job_index=i,
                    title=j.title,
                    company=j.company or "",
                    description=(j.raw_data or {}).get("job_description", ""),
                    requirements=(j.raw_data or {}).get("job_requirements", ""),
                    location=j.location or "",
                )
                for i, j in enumerate(unscored_jobs)
            ]

            scores = await matching.score_jobs(resume_data, job_data_list)

            # Update jobs with scores
            score_map = {s.job_index: s for s in scores}
            for i, job in enumerate(unscored_jobs):
                if i in score_map:
                    s = score_map[i]
                    job.match_score = s.score
                    job.match_rationale = s.rationale
                    if s.sponsorship != "unknown":
                        job.sponsorship = s.sponsorship
                    if s.country != "unknown":
                        job.country = s.country
                    job.updated_at = datetime.now(UTC)

            await db.commit()
            return {"status": "completed", "scored": len(scores)}

    return run_async(_score())


@celery_app.task(name="app.workers.tasks.score_linkedin_posts")
def score_linkedin_posts(user_id: str) -> dict:
    """Score unscored LinkedIn posts for a user."""

    async def _score() -> dict:
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.linkedin_post import LinkedInPost
        from app.models.resume import Resume
        from app.services.groq_matching_service import GroqMatchingService
        from app.services.matching_service import PostData, ResumeData

        matching = GroqMatchingService()

        async with async_session_factory() as db:
            # Get user's parsed resume
            result = await db.execute(
                select(Resume).where(Resume.user_id == user_id)
            )
            resume = result.scalar_one_or_none()
            if not resume or not resume.parsed_data:
                return {"status": "skipped", "reason": "no parsed resume"}

            resume_data = ResumeData(
                skills=resume.parsed_data.get("skills", []),
                roles=resume.parsed_data.get("roles", []),
                years_of_experience=resume.parsed_data.get("years_of_experience", 0),
            )

            # Get unscored posts
            result = await db.execute(
                select(LinkedInPost).where(
                    LinkedInPost.user_id == user_id,
                    LinkedInPost.scored_at.is_(None),
                )
            )
            unscored = list(result.scalars().all())

            if not unscored:
                return {"status": "skipped", "reason": "no unscored posts"}

            post_data_list = [
                PostData(
                    post_index=i,
                    raw_text=p.raw_text,
                    poster_name=p.poster_name or "",
                )
                for i, p in enumerate(unscored)
            ]

            scores = await matching.score_linkedin_posts(resume_data, post_data_list)

            score_map = {s.post_index: s for s in scores}
            for i, post in enumerate(unscored):
                if i in score_map:
                    s = score_map[i]
                    post.match_score = s.score
                    post.match_rationale = s.rationale
                    if s.sponsorship != "unknown":
                        post.sponsorship = s.sponsorship
                    if s.country != "unknown":
                        post.country = s.country
                    post.scored_at = datetime.now(UTC)
                    post.updated_at = datetime.now(UTC)

            await db.commit()
            return {"status": "completed", "scored": len(scores)}

    return run_async(_score())


@celery_app.task(name="app.workers.tasks.parse_resume")
def parse_resume(user_id: str, text: str) -> dict:
    """Parse resume text via LLM and store structured data."""

    async def _parse() -> dict:
        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.resume import Resume
        from app.services.groq_matching_service import GroqMatchingService

        matching = GroqMatchingService()

        async with async_session_factory() as db:
            result = await db.execute(
                select(Resume).where(Resume.user_id == user_id)
            )
            resume = result.scalar_one_or_none()
            if not resume:
                return {"status": "error", "reason": "resume not found"}

            resume_data = await matching.parse_resume(text)
            resume.parsed_data = {
                "skills": resume_data.skills,
                "experience": resume_data.experience,
                "education": resume_data.education,
                "roles": resume_data.roles,
                "years_of_experience": resume_data.years_of_experience,
                "raw_text": text[:5000],
            }
            resume.updated_at = datetime.now(UTC)
            await db.commit()

            return {"status": "completed"}

    return run_async(_parse())


@celery_app.task(name="app.workers.job_fetch_task.fetch_jobs_for_all_users")
def fetch_jobs_for_all_users() -> dict:
    """Daily job fetch: iterate all users and fetch from JSearch."""

    async def _fetch() -> dict:
        import redis.asyncio as aioredis
        from sqlalchemy import select

        from app.core.config import get_settings
        from app.core.database import async_session_factory
        from app.models.user import User
        from app.services.job_fetch_service import JobFetchService

        settings = get_settings()
        fetch_service = JobFetchService()
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

        total_new = 0
        async with async_session_factory() as db:
            result = await db.execute(select(User))
            users = list(result.scalars().all())

            for user in users:
                try:
                    new_count = await fetch_service.fetch_for_user(db, redis, user)
                    total_new += new_count

                    # Queue scoring if new jobs were fetched
                    if new_count > 0:
                        score_jobs_for_user.delay(str(user.id))

                except Exception as e:
                    logger.error(
                        "Job fetch failed for user",
                        user_id=str(user.id),
                        error=str(e),
                    )

            await db.commit()

        await redis.close()
        return {"status": "completed", "users": len(users), "new_jobs": total_new}

    return run_async(_fetch())
