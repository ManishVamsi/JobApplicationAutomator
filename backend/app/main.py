"""FastAPI application factory with lifespan, middleware, and router registration."""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.api import admin, auth, health, jobs, linkedin, portals, users
from app.core.config import get_settings
from app.core.logging import RequestIdMiddleware, setup_logging
from app.core.middleware import setup_cors


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    setup_logging()

    from app.core.logging import get_logger

    logger = get_logger("app")
    logger.info("Starting Job Application Automator", environment=settings.ENVIRONMENT.value)

    yield

    # Shutdown: close Redis connection
    from app.api.deps import _redis_client

    if _redis_client is not None:
        await _redis_client.close()

    logger.info("Shutdown complete")


settings = get_settings()

app = FastAPI(
    title="Job Application Automator",
    description="Multi-tenant job discovery, tracking, and LLM-based matching",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_local else None,
    redoc_url="/redoc" if settings.is_local else None,
)

# Middleware
setup_cors(app)
app.add_middleware(RequestIdMiddleware)

# Routers — all under /api/v1
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(portals.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(linkedin.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.get("/")
async def root() -> dict:
    """Root endpoint — basic info."""
    return {
        "app": "Job Application Automator",
        "version": "0.1.0",
        "docs": "/docs" if settings.is_local else "disabled in production",
    }
