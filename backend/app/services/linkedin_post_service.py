"""LinkedIn post service — ingestion, dedup, and threshold filtering."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.linkedin_post import LinkedInPost, PostSource

logger = get_logger(__name__)
settings = get_settings()


class LinkedInPostService:
    """Business logic for LinkedIn hiring post ingestion and querying."""

    async def ingest_post(
        self,
        db: AsyncSession,
        user_id: str,
        post_url: str | None,
        raw_text: str,
        poster_name: str | None,
        source: PostSource,
    ) -> LinkedInPost | None:
        """Ingest a LinkedIn post, dedup by post_url per user.

        Returns the post if new, None if duplicate.
        """
        # Dedup check
        if post_url:
            result = await db.execute(
                select(LinkedInPost).where(
                    LinkedInPost.user_id == user_id,
                    LinkedInPost.post_url == post_url,
                )
            )
            if result.scalar_one_or_none() is not None:
                logger.debug("Duplicate post skipped", user_id=user_id, post_url=post_url)
                return None

        post = LinkedInPost(
            user_id=user_id,
            post_url=post_url,
            poster_name=poster_name,
            raw_text=raw_text[:5000],  # Cap text length
            source=source,
            submitted_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(post)
        await db.flush()

        logger.info("LinkedIn post ingested", user_id=user_id, source=source.value)
        return post

    async def get_scored_posts(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        min_score: float | None = None,
        country: str | None = None,
        sponsorship: str | None = None,
    ) -> tuple[list[LinkedInPost], int]:
        """Get scored posts above the threshold, with optional filters.

        Returns (posts, total_count).
        """
        threshold = min_score or settings.MATCH_SCORE_THRESHOLD

        query = (
            select(LinkedInPost)
            .where(
                LinkedInPost.user_id == user_id,
                LinkedInPost.scored_at.is_not(None),
                LinkedInPost.match_score >= threshold,
            )
            .order_by(LinkedInPost.match_score.desc())
        )

        if country:
            query = query.where(LinkedInPost.country == country)
        if sponsorship:
            query = query.where(LinkedInPost.sponsorship == sponsorship)

        # Count total
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        posts = list(result.scalars().all())

        return posts, total

    async def get_unscored_posts(
        self, db: AsyncSession, user_id: str | None = None
    ) -> list[LinkedInPost]:
        """Get all unscored posts (for the scoring task)."""
        query = select(LinkedInPost).where(LinkedInPost.scored_at.is_(None))
        if user_id:
            query = query.where(LinkedInPost.user_id == user_id)
        result = await db.execute(query)
        return list(result.scalars().all())
