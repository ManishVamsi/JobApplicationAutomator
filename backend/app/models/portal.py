"""Portal model — job portal connections with encrypted credentials."""

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PortalType(str, enum.Enum):
    NAUKRI = "naukri"
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    SEEK = "seek"
    GLASSDOOR = "glassdoor"
    OTHER = "other"


class PortalStatus(str, enum.Enum):
    CONNECTED = "connected"
    NEEDS_REAUTH = "needs_reauth"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class Portal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A connected job portal with encrypted credentials (envelope encryption)."""

    __tablename__ = "portals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    portal_type: Mapped[PortalType] = mapped_column(
        Enum(PortalType, name="portal_type_enum"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PortalStatus] = mapped_column(
        Enum(PortalStatus, name="portal_status_enum"),
        nullable=False,
        default=PortalStatus.CONNECTED,
    )

    # Encrypted credentials — envelope encryption (Fernet)
    # encrypted_data_key: per-user data key, encrypted with the master key
    # credentials_encrypted: portal password/token, encrypted with the per-user data key
    encrypted_data_key: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    credentials_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    oauth_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="portals")  # noqa: F821
    jobs: Mapped[list["Job"]] = relationship(back_populates="portal")  # noqa: F821
