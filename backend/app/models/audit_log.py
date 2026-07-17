"""Audit log models — append-only general audit and credential access log."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """General append-only audit log for significant user/system actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CredentialAccessLog(UUIDPrimaryKeyMixin, Base):
    """Separate append-only log for every credential encrypt/decrypt/delete operation."""

    __tablename__ = "credential_access_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    portal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portals.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="encrypt | decrypt | delete | master_key_rotation"
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
