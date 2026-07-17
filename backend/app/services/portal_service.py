"""Portal service — CRUD operations with envelope-encrypted credentials."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import CredentialAccessLog
from app.models.portal import Portal, PortalStatus, PortalType
from app.services.encryption_service import EncryptionService

logger = get_logger(__name__)


class PortalService:
    """Business logic for managing job portal connections."""

    def __init__(self) -> None:
        self._encryption = EncryptionService()

    async def create_portal(
        self,
        db: AsyncSession,
        user_id: str,
        portal_type: PortalType,
        display_name: str,
        credentials: str | None = None,
        ip_address: str | None = None,
    ) -> Portal:
        """Create a new portal connection with encrypted credentials."""
        encrypted_data_key = None
        credentials_encrypted = None

        if credentials:
            encrypted_data_key, credentials_encrypted = (
                self._encryption.encrypt_for_storage(credentials)
            )
            # Log credential encryption
            await self._log_credential_access(
                db, user_id, None, "encrypt", ip_address
            )

        portal = Portal(
            user_id=user_id,
            portal_type=portal_type,
            display_name=display_name,
            status=PortalStatus.CONNECTED,
            encrypted_data_key=encrypted_data_key,
            credentials_encrypted=credentials_encrypted,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(portal)
        await db.flush()

        logger.info("Portal created", user_id=user_id, portal_type=portal_type.value)
        return portal

    async def list_portals(
        self, db: AsyncSession, user_id: str
    ) -> list[Portal]:
        """List all portals for a user (without decrypted credentials)."""
        result = await db.execute(
            select(Portal).where(Portal.user_id == user_id).order_by(Portal.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_portal(
        self,
        db: AsyncSession,
        user_id: str,
        portal_id: str,
        ip_address: str | None = None,
    ) -> None:
        """Delete a portal and its encrypted credentials."""
        result = await db.execute(
            select(Portal).where(Portal.id == portal_id, Portal.user_id == user_id)
        )
        portal = result.scalar_one_or_none()

        if portal is None:
            raise ValueError("Portal not found")

        # Log credential deletion
        if portal.encrypted_data_key:
            await self._log_credential_access(
                db, user_id, portal_id, "delete", ip_address
            )

        await db.delete(portal)
        logger.info("Portal deleted", user_id=user_id, portal_id=portal_id)

    async def decrypt_credentials(
        self,
        db: AsyncSession,
        user_id: str,
        portal_id: str,
        ip_address: str | None = None,
    ) -> str:
        """Decrypt and return portal credentials (for internal use only)."""
        result = await db.execute(
            select(Portal).where(Portal.id == portal_id, Portal.user_id == user_id)
        )
        portal = result.scalar_one_or_none()

        if portal is None or not portal.encrypted_data_key or not portal.credentials_encrypted:
            raise ValueError("Portal not found or no credentials stored")

        # Log credential access
        await self._log_credential_access(
            db, user_id, portal_id, "decrypt", ip_address
        )

        return self._encryption.decrypt_from_storage(
            portal.encrypted_data_key, portal.credentials_encrypted
        )

    async def _log_credential_access(
        self,
        db: AsyncSession,
        user_id: str,
        portal_id: str | None,
        action: str,
        ip_address: str | None,
    ) -> None:
        """Log a credential access event to the separate audit log."""
        log_entry = CredentialAccessLog(
            user_id=user_id,
            portal_id=portal_id,
            action=action,
            ip_address=ip_address,
            timestamp=datetime.now(UTC),
        )
        db.add(log_entry)
