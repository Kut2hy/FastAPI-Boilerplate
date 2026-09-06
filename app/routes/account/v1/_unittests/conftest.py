"""Fixtures shared by the forgotten password route tests.

Both fixtures run on the session event loop, so every test module in this package must declare
``pytestmark = pytest.mark.asyncio(loop_scope="session")``.
"""

import os
from typing import TYPE_CHECKING

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.app_config import APP_SETTINGS
from app.core.redis.dependencies import IN_STATE_NAME
from app.main import app as main_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

SERVER_URL = f"http://{APP_SETTINGS.host}:{APP_SETTINGS.port}"
"""Base URL for the test server. Must match host for trusted host middleware to allow requests through."""

REDIS_TEST_DB = 15
"""Redis database reserved for tests, kept away from the application's default database."""


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def redis_client() -> AsyncGenerator[Redis]:
    """Attach a clean test Redis client to the app state, mirroring what the lifespan does on startup."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=REDIS_TEST_DB,
        decode_responses=True,
    )

    await client.ping()
    await client.flushdb()

    setattr(main_app.state, IN_STATE_NAME, client)

    yield client

    delattr(main_app.state, IN_STATE_NAME)

    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture(loop_scope="session")
async def app_client() -> AsyncGenerator[AsyncClient]:
    """Drive the ASGI app in the running test event loop, so it shares the loop with the Redis fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=main_app),
        base_url=SERVER_URL,
    ) as client:
        yield client
