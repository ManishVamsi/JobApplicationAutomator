"""Pydantic schemas for user endpoints."""

from pydantic import BaseModel


class UserProfile(BaseModel):
    """User profile response."""

    id: str
    email: str
    name: str | None = None
    target_roles: list[str] = []
    target_locations: list[str] = []
    work_auth_status: str | None = None
    created_at: str


class UserUpdate(BaseModel):
    """User profile update request."""

    name: str | None = None
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    work_auth_status: str | None = None


class ApiTokenResponse(BaseModel):
    """Response when generating a new API token — shown once."""

    token: str
    message: str


class ApiTokenInfo(BaseModel):
    """API token metadata (prefix only — never the raw token)."""

    prefix: str
    created_at: str
    last_used_at: str | None = None
