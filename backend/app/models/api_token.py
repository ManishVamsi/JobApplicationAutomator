"""ApiToken model — long-lived, revocable tokens for the browser extension."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class ApiToken(UUIDPrimaryKeyMixin, Base):
    """Long-lived, revocable API token for the browser extension.

    The raw token is shown once at creation and never stored —
    only the SHA-256 hash is persisted (like a password).
    """

    __tablename__ = "api_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True,
        comment="SHA-256 hash of the raw token"
    )
    prefix: Mapped[str] = mapped_column(
        String(16), nullable=False,
        comment="First 12 chars of the raw token, for display: jaa_Ab3k..."
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_tokens")  # noqa: F821
