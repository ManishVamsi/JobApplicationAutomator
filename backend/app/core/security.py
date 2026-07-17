"""JWT token creation/verification and OTP generation.

Uses PyJWT (not python-jose) for all JWT operations.
Enforces token type claims to prevent token confusion attacks.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import get_settings

settings = get_settings()

# --------------------------------------------------------------------------- #
# JWT Tokens
# --------------------------------------------------------------------------- #

ALGORITHM = "HS256"


def create_access_token(user_id: str) -> str:
    """Create a short-lived access token (default 15 min)."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Create a long-lived refresh token (default 7 days).

    Returns:
        Tuple of (encoded_token, jti) — the JTI must be stored in Redis
        for allowlist-based revocation.
    """
    now = datetime.now(UTC)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token.

    Enforces type == "access" to prevent token confusion
    (a refresh token used as an access token).

    Raises:
        InvalidTokenError: If the token is invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise

    if payload.get("type") != "access":
        raise InvalidTokenError("Token type must be 'access'")

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token.

    Enforces type == "refresh" to prevent token confusion
    (an access token used as a refresh token).

    Raises:
        InvalidTokenError: If the token is invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise

    if payload.get("type") != "refresh":
        raise InvalidTokenError("Token type must be 'refresh'")

    return payload


def verify_csrf_access_token(
    token: str,
    expected_user_id: str,
    max_age_hours: int | None = None,
) -> dict[str, Any]:
    """Verify an access token used as CSRF proof on /auth/refresh.

    - Signature is verified (HS256).
    - Expiry is NOT enforced (the token is expected to be expired).
    - Token type must be "access".
    - sub must match expected_user_id.
    - Token must not be older than max_age_hours (staleness ceiling).

    Raises:
        InvalidTokenError: If any check fails.
    """
    if max_age_hours is None:
        max_age_hours = settings.CSRF_MAX_TOKEN_AGE_HOURS

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
    except InvalidTokenError:
        raise

    if payload.get("type") != "access":
        raise InvalidTokenError("CSRF proof must be an access token")

    if payload.get("sub") != expected_user_id:
        raise InvalidTokenError("CSRF token sub does not match refresh token user")

    # Staleness ceiling: reject tokens expired more than max_age_hours ago
    exp = payload.get("exp")
    if exp is not None:
        exp_dt = datetime.fromtimestamp(exp, tz=UTC)
        staleness_limit = datetime.now(UTC) - timedelta(hours=max_age_hours)
        if exp_dt < staleness_limit:
            raise InvalidTokenError(
                f"CSRF access token expired more than {max_age_hours}h ago"
            )

    return payload


# --------------------------------------------------------------------------- #
# OTP
# --------------------------------------------------------------------------- #


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return f"{secrets.randbelow(1_000_000):06d}"


# --------------------------------------------------------------------------- #
# API Token (for browser extension)
# --------------------------------------------------------------------------- #

API_TOKEN_PREFIX = "jaa_"


def generate_api_token() -> tuple[str, str]:
    """Generate a long-lived API token for the browser extension.

    Returns:
        Tuple of (raw_token, token_hash).
        The raw token is shown once to the user; only the hash is stored.
    """
    random_part = secrets.token_hex(32)
    raw_token = f"{API_TOKEN_PREFIX}{random_part}"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_api_token(raw_token: str) -> str:
    """Hash an API token for lookup."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def get_api_token_prefix(raw_token: str) -> str:
    """Extract the display prefix (first 12 chars) from a raw API token."""
    return raw_token[:12] + "..."
