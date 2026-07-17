"""Encryption service tests — envelope encryption roundtrip and key rotation."""

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.services.encryption_service import EncryptionService


class TestEnvelopeEncryption:
    """Test the envelope encryption scheme used for portal credentials."""

    def test_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypt → store → decrypt → verify plaintext matches."""
        svc = EncryptionService()
        plaintext = "my-super-secret-password"

        encrypted_dk, encrypted_cred = svc.encrypt_for_storage(plaintext)

        assert encrypted_dk != plaintext.encode()
        assert encrypted_cred != plaintext.encode()

        decrypted = svc.decrypt_from_storage(encrypted_dk, encrypted_cred)
        assert decrypted == plaintext

    def test_reuse_data_key(self) -> None:
        """Re-encrypting with the same data key should produce decryptable ciphertext."""
        svc = EncryptionService()
        plaintext1 = "password-one"
        plaintext2 = "password-two"

        dk, cred1 = svc.encrypt_for_storage(plaintext1)
        _, cred2 = svc.encrypt_for_storage(plaintext2, existing_data_key_encrypted=dk)

        assert svc.decrypt_from_storage(dk, cred1) == plaintext1
        assert svc.decrypt_from_storage(dk, cred2) == plaintext2

    def test_different_data_keys_per_call(self) -> None:
        """Each encrypt_for_storage call without existing key generates a new data key."""
        svc = EncryptionService()

        dk1, _ = svc.encrypt_for_storage("a")
        dk2, _ = svc.encrypt_for_storage("b")

        assert dk1 != dk2

    def test_wrong_master_key_fails(self) -> None:
        """Decryption with wrong master key should fail with InvalidToken."""
        svc = EncryptionService()
        dk, cred = svc.encrypt_for_storage("secret")

        # Simulate wrong master key
        wrong_key = Fernet.generate_key()
        svc._master_fernet = Fernet(wrong_key)

        with pytest.raises(InvalidToken):
            svc.decrypt_from_storage(dk, cred)


class TestKeyRotation:
    """Test the key rotation workflow (encrypt with A → rotate to B → decrypt with B)."""

    def test_key_rotation_roundtrip(self) -> None:
        """Simulate the rotate_master_key.py script logic."""
        old_master = Fernet.generate_key()
        new_master = Fernet.generate_key()

        # Encrypt with old master key
        old_fernet = Fernet(old_master)
        data_key = Fernet.generate_key()
        encrypted_dk_old = old_fernet.encrypt(data_key)

        # Encrypt credential with data key
        data_fernet = Fernet(data_key)
        plaintext = "my-portal-password"
        encrypted_cred = data_fernet.encrypt(plaintext.encode())

        # Simulate rotation: decrypt data key with old master, re-encrypt with new
        decrypted_dk = old_fernet.decrypt(encrypted_dk_old)
        assert decrypted_dk == data_key

        new_fernet = Fernet(new_master)
        encrypted_dk_new = new_fernet.encrypt(decrypted_dk)

        # Verify: decrypt data key with new master, then decrypt credential
        recovered_dk = new_fernet.decrypt(encrypted_dk_new)
        assert recovered_dk == data_key

        recovered_plaintext = Fernet(recovered_dk).decrypt(encrypted_cred).decode()
        assert recovered_plaintext == plaintext

    def test_old_key_fails_after_rotation(self) -> None:
        """After rotation, old master key cannot decrypt the re-encrypted data key."""
        old_master = Fernet.generate_key()
        new_master = Fernet.generate_key()

        old_fernet = Fernet(old_master)
        data_key = Fernet.generate_key()
        encrypted_dk_old = old_fernet.encrypt(data_key)

        # Rotate
        decrypted_dk = old_fernet.decrypt(encrypted_dk_old)
        new_fernet = Fernet(new_master)
        encrypted_dk_new = new_fernet.encrypt(decrypted_dk)

        # Old key should NOT decrypt the new-key-encrypted data key
        with pytest.raises(InvalidToken):
            old_fernet.decrypt(encrypted_dk_new)
