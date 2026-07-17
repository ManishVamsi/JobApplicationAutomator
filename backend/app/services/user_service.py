"""User service — profile management and API token lifecycle."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import generate_api_token, get_api_token_prefix
from app.models.api_token import ApiToken
from app.models.user import User

logger = get_logger(__name__)


class UserService:
    """Business logic for user profile and API token management."""

    async def get_profile(self, db: AsyncSession, user_id: str) -> User | None:
        """Get a user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        db: AsyncSession,
        user_id: str,
        name: str | None = None,
        target_roles: list[str] | None = None,
        target_locations: list[str] | None = None,
        work_auth_status: str | None = None,
    ) -> User:
        """Update user profile fields."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError("User not found")

        if name is not None:
            user.name = name
        if target_roles is not None:
            user.target_roles = target_roles
        if target_locations is not None:
            user.target_locations = target_locations
        if work_auth_status is not None:
            user.work_auth_status = work_auth_status

        user.updated_at = datetime.now(UTC)
        return user

    async def generate_api_token(
        self, db: AsyncSession, user_id: str
    ) -> str:
        """Generate or rotate a long-lived API token for the browser extension.

        - If a token exists, revokes it (sets revoked_at) and creates a new one.
        - Returns the raw token ONCE — it cannot be retrieved again.
        - Only the SHA-256 hash is stored.
        """
        # Revoke existing tokens
        result = await db.execute(
            select(ApiToken).where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
        )
        existing = result.scalars().all()
        for token in existing:
            token.revoked_at = datetime.now(UTC)

        # Generate new token
        raw_token, token_hash = generate_api_token()
        prefix = get_api_token_prefix(raw_token)

        api_token = ApiToken(
            user_id=user_id,
            token_hash=token_hash,
            prefix=prefix,
            created_at=datetime.now(UTC),
        )
        db.add(api_token)
        await db.flush()

        logger.info("API token generated", user_id=user_id, prefix=prefix)
        return raw_token

    async def revoke_api_token(
        self, db: AsyncSession, user_id: str
    ) -> bool:
        """Revoke the current API token without generating a new one."""
        result = await db.execute(
            select(ApiToken).where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return False

        token.revoked_at = datetime.now(UTC)
        logger.info("API token revoked", user_id=user_id)
        return True

    async def get_api_token_info(
        self, db: AsyncSession, user_id: str
    ) -> dict | None:
        """Get the current API token's metadata (prefix, created_at, last_used_at)."""
        result = await db.execute(
            select(ApiToken).where(
                ApiToken.user_id == user_id,
                ApiToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None

        return {
            "prefix": token.prefix,
            "created_at": token.created_at.isoformat(),
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
        }
