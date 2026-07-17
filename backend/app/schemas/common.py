"""Pydantic schemas shared across multiple endpoints."""

from pydantic import BaseModel


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    """Wrapper for paginated responses."""

    total: int
    page: int
    page_size: int
    items: list  # type: ignore[type-arg]


class HealthResponse(BaseModel):
    """Response from /healthz endpoint."""

    status: str
    database: str
    redis: str
    jsearch_quota: dict | None = None
    last_job_fetch: str | None = None
