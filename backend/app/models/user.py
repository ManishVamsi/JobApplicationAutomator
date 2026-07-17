"""User model — profile and auth data."""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Application user with profile and job search preferences."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    target_locations: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    work_auth_status: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    portals: Mapped[list["Portal"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    linkedin_posts: Mapped[list["LinkedInPost"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    api_tokens: Mapped[list["ApiToken"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
