"""Pydantic schemas for job endpoints."""

from pydantic import BaseModel


class JobResponse(BaseModel):
    """Job listing response."""

    id: str
    title: str
    company: str | None = None
    location: str | None = None
    country: str | None = None
    url: str | None = None
    match_score: float | None = None
    match_rationale: str | None = None
    sponsorship: str = "unknown"
    fetched_at: str
