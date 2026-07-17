"""Resume model — metadata + parsed data. File bytes stored in object storage, not Postgres."""

import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User's resume. File stored in S3-compatible object storage; DB holds only metadata."""

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(
        Text, nullable=False, comment="S3/object storage key — no raw bytes in Postgres"
    )
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="resumes")  # noqa: F821
