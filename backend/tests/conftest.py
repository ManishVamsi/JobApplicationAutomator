"""Test fixtures — test DB, test client, authenticated user helpers."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Helper: returns Authorization headers with a valid access token.

    For tests that need an authenticated user without going through
    the full OTP flow.
    """
    from app.core.security import create_access_token

    # Create a test user directly
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    return {"Authorization": f"Bearer {token}"}
