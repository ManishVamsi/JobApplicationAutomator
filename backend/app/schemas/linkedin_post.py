"""Pydantic schemas for LinkedIn post endpoints."""

from pydantic import BaseModel


class LinkedInPostIngest(BaseModel):
    """Request body for ingesting a LinkedIn post."""

    post_url: str | None = None
    raw_text: str
    poster_name: str | None = None


class LinkedInPostResponse(BaseModel):
    """LinkedIn post response."""

    id: str
    post_url: str | None = None
    poster_name: str | None = None
    raw_text: str
    match_score: float | None = None
    match_rationale: str | None = None
    country: str | None = None
    sponsorship: str = "unknown"
    source: str
    submitted_at: str
    scored_at: str | None = None
