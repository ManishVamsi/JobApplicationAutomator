"""LinkedIn post model — ingested via browser extension or manual add."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.job import SponsorshipStatus


class PostSource(str, enum.Enum):
    EXTENSION = "extension"
    MANUAL = "manual"


class LinkedInPost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A LinkedIn hiring post, ingested via the browser extension or manual paste."""

    __tablename__ = "linkedin_posts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sponsorship: Mapped[SponsorshipStatus] = mapped_column(
        Enum(SponsorshipStatus, name="sponsorship_status_enum", create_type=False),
        nullable=False,
        default=SponsorshipStatus.UNKNOWN,
    )
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[PostSource] = mapped_column(
        Enum(PostSource, name="post_source_enum"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="linkedin_posts")  # noqa: F821
