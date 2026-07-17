"""Envelope encryption for portal credentials.

Uses Fernet (symmetric, authenticated encryption) in a two-layer scheme:
1. Per-user data key (random Fernet key)
2. Master key (from env ENCRYPTION_MASTER_KEY) encrypts the data key
3. Data key encrypts the actual credential

CAUTION: Rotating ENCRYPTION_MASTER_KEY requires running the re-encryption
script first — see README.md "Operational Runbook" section.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Envelope encryption service for portal credentials."""

    def __init__(self) -> None:
        settings = get_settings()
        self._master_key = settings.ENCRYPTION_MASTER_KEY.encode()
        self._master_fernet = Fernet(self._master_key)

    def generate_data_key(self) -> bytes:
        """Generate a new per-user Fernet data key."""
        return Fernet.generate_key()

    def encrypt_data_key(self, data_key: bytes) -> bytes:
        """Encrypt a data key with the master key."""
        return self._master_fernet.encrypt(data_key)

    def decrypt_data_key(self, encrypted_data_key: bytes) -> bytes:
        """Decrypt a data key using the master key.

        Raises:
            InvalidToken: If the master key doesn't match (e.g., key was rotated
            without running the re-encryption script).
        """
        try:
            return self._master_fernet.decrypt(encrypted_data_key)
        except InvalidToken:
            logger.error(
                "Failed to decrypt data key — master key mismatch. "
                "Did you rotate ENCRYPTION_MASTER_KEY without running "
                "the re-encryption script?"
            )
            raise

    def encrypt_credential(self, data_key: bytes, plaintext: str) -> bytes:
        """Encrypt a credential with the per-user data key."""
        f = Fernet(data_key)
        return f.encrypt(plaintext.encode())

    def decrypt_credential(self, data_key: bytes, ciphertext: bytes) -> str:
        """Decrypt a credential with the per-user data key."""
        f = Fernet(data_key)
        return f.decrypt(ciphertext).decode()

    def encrypt_for_storage(
        self, plaintext: str, existing_data_key_encrypted: bytes | None = None
    ) -> tuple[bytes, bytes]:
        """Full encrypt flow: generate or reuse data key, encrypt credential.

        Args:
            plaintext: The credential to encrypt.
            existing_data_key_encrypted: If provided, reuse this data key
                (decrypt it first). Otherwise, generate a new one.

        Returns:
            Tuple of (encrypted_data_key, encrypted_credential).
        """
        if existing_data_key_encrypted is not None:
            data_key = self.decrypt_data_key(existing_data_key_encrypted)
        else:
            data_key = self.generate_data_key()

        encrypted_data_key = self.encrypt_data_key(data_key)
        encrypted_credential = self.encrypt_credential(data_key, plaintext)

        return encrypted_data_key, encrypted_credential

    def decrypt_from_storage(
        self, encrypted_data_key: bytes, encrypted_credential: bytes
    ) -> str:
        """Full decrypt flow: decrypt data key, then decrypt credential."""
        data_key = self.decrypt_data_key(encrypted_data_key)
        return self.decrypt_credential(data_key, encrypted_credential)
