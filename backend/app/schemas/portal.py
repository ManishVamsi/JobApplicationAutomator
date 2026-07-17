"""Pydantic schemas for portal endpoints."""

from pydantic import BaseModel


class PortalCreate(BaseModel):
    """Request body for creating a portal connection."""

    portal_type: str  # naukri | linkedin | indeed | seek | glassdoor | other
    display_name: str
    credentials: str | None = None


class PortalResponse(BaseModel):
    """Portal info response (never includes decrypted credentials)."""

    id: str
    portal_type: str
    display_name: str
    status: str
    created_at: str
