"""Job model — aggregated job listings from JSearch and portals."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SponsorshipStatus(str, enum.Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A job listing fetched from JSearch or a portal, scored by the LLM."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_job_user_external"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    portal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portals.id", ondelete="SET NULL"), nullable=True
    )
    external_id: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 of description — for future cross-portal dedup"
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sponsorship: Mapped[SponsorshipStatus] = mapped_column(
        Enum(SponsorshipStatus, name="sponsorship_status_enum"),
        nullable=False,
        default=SponsorshipStatus.UNKNOWN,
    )
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="jobs")  # noqa: F821
    portal: Mapped["Portal | None"] = relationship(back_populates="jobs")  # noqa: F821
