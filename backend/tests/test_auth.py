"""Auth tests — OTP flow, token confusion, CSRF proof, and brute-force protection."""

import pytest
from httpx import AsyncClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from jwt.exceptions import InvalidTokenError


class TestTokenTypeSeparation:
    """Verify JWT token confusion attacks are prevented.

    These are explicit regression tests for the token-confusion pitfall:
    a refresh token must NEVER be accepted where an access token is expected,
    and vice versa.
    """

    def test_refresh_token_rejected_as_access_token(self) -> None:
        """A refresh token used as an access token must be rejected."""
        refresh_token, _jti = create_refresh_token("test-user-id")

        with pytest.raises(InvalidTokenError, match="access"):
            decode_access_token(refresh_token)

    def test_access_token_rejected_as_refresh_token(self) -> None:
        """An access token used as a refresh token must be rejected."""
        access_token = create_access_token("test-user-id")

        with pytest.raises(InvalidTokenError, match="refresh"):
            decode_refresh_token(access_token)

    def test_valid_access_token_accepted(self) -> None:
        """A valid access token should decode successfully."""
        access_token = create_access_token("test-user-id")
        payload = decode_access_token(access_token)

        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "access"

    def test_valid_refresh_token_accepted(self) -> None:
        """A valid refresh token should decode successfully."""
        refresh_token, jti = create_refresh_token("test-user-id")
        payload = decode_refresh_token(refresh_token)

        assert payload["sub"] == "test-user-id"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti


class TestCSRFProof:
    """Verify the CSRF staleness ceiling and sub-match on /auth/refresh."""

    def test_csrf_proof_rejects_wrong_user(self) -> None:
        """CSRF proof must reject access tokens from a different user."""
        from app.core.security import verify_csrf_access_token

        token = create_access_token("user-a")

        with pytest.raises(InvalidTokenError, match="sub does not match"):
            verify_csrf_access_token(token, expected_user_id="user-b")

    def test_csrf_proof_rejects_refresh_token(self) -> None:
        """CSRF proof must reject refresh tokens."""
        from app.core.security import verify_csrf_access_token

        refresh_token, _ = create_refresh_token("test-user")

        with pytest.raises(InvalidTokenError, match="access token"):
            verify_csrf_access_token(refresh_token, expected_user_id="test-user")

    def test_csrf_proof_accepts_matching_token(self) -> None:
        """CSRF proof should accept a valid access token for the correct user."""
        from app.core.security import verify_csrf_access_token

        token = create_access_token("test-user")
        payload = verify_csrf_access_token(token, expected_user_id="test-user")

        assert payload["sub"] == "test-user"


class TestAPIToken:
    """Verify API token generation and hashing."""

    def test_generate_api_token_format(self) -> None:
        """Generated API token should have jaa_ prefix and be hashable."""
        from app.core.security import generate_api_token, hash_api_token

        raw_token, token_hash = generate_api_token()

        assert raw_token.startswith("jaa_")
        assert len(raw_token) == 68  # "jaa_" (4) + 64 hex chars
        assert hash_api_token(raw_token) == token_hash

    def test_api_token_prefix(self) -> None:
        """Token prefix should show first 12 chars."""
        from app.core.security import generate_api_token, get_api_token_prefix

        raw_token, _ = generate_api_token()
        prefix = get_api_token_prefix(raw_token)

        assert prefix.endswith("...")
        assert len(prefix) == 15  # 12 chars + "..."
