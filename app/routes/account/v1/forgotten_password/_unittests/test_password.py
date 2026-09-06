"""Test suite for the password module in the forgotten password feature of the account v1 routes."""

import os
from typing import TYPE_CHECKING
from uuid import uuid7

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from fastapi import HTTPException
from traitlets import default
from app.app_config import APP_SETTINGS
from app.core.jwt.access_token import AccessToken
from app.core.jwt.refresh_token import RefreshToken
from app.core.redis.dependencies import IN_STATE_NAME
from app.core.redis.session import create_session, SESSION_KEY_TEMPLATE
from app.core.redis.limiter import ATTEMPTS_LIMIT
from app.core.redis.session import SESSION_KEY_TEMPLATE
from app.core.templating.v1._unittests.test_full_responses import TEST_DEFAULT_FRAGMENT_TEMPLATES
from app.main import app as main_app
from app.piccolo.tables import user_account

from .. import email
from .. import password
from ..__constants import (
    FORGOTTEN_PASSW_COOKIE_NAME,
    FORGOTTEN_PASSW_FS_PATH_PARTS,
    FORGOTTEN_PASSW_KEY_TTL,
    FORGOTTEN_PASSW_PREFIX,
    FORGOTTEN_PASSW_URL,
)
from piccolo.table import create_db_tables, drop_db_tables
from piccolo.conf.apps import Finder
from piccolo.testing.model_builder import ModelBuilder

TABLES = Finder().get_table_classes()

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

pytestmark = pytest.mark.asyncio

SERVER_URL = f"http://{APP_SETTINGS.host}:{APP_SETTINGS.port}"
"""Base URL for the test server. Must match host for trusted host middleware to allow requests through."""

BASE_URL = password.FORGOTTEN_PASSW_URL + f"/{password.CURRENT_ENDPOINT}"
"""Base URL for the forgotten password password route being tested."""

TEST_USER_UUID = uuid7()
"""UUID for a test user, used in generating tokens for authenticated requests."""

TEST_ACCESS_TOKEN = AccessToken.generate_token(subject=TEST_USER_UUID, alias="test_user", roles="")
"""Access token for the test user, used in authenticated requests."""

TEST_REFRESH_TOKEN = RefreshToken.generate_token(subject=TEST_USER_UUID)
"""Refresh token for the test user, used in authenticated requests."""

TEST_URL_TOKEN = "test-url-token"  # noqa: S105
"""URL token for the test user, used in authenticated requests."""

TEST_SESSION_KEY = SESSION_KEY_TEMPLATE % {"prefix": email.FORGOTTEN_PASSW_PREFIX, "url_token": TEST_URL_TOKEN}
"""Redis session key for the test user's forgotten password session."""

TEST_EMAIL = "test@example.com"
"""Email for the test user, used in generating tokens and sessions."""

TEST_PASSWORD = "TestPassword123!"  # noqa: S105
"""Password for the test user, used in password reset tests."""


# @pytest_asyncio.fixture(autouse=True)
# async def create_tables(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[None]:
#     """Create and drop database tables for the tests."""
#     _user_account = await ModelBuilder.build(
#         user_account.UserAccount,
#         persist=False,
#         defaults={
#             "id": TEST_USER_UUID,
#             "email": TEST_EMAIL,
#         },
#     )

#     yield


@pytest_asyncio.fixture(autouse=True)
async def redis_client() -> AsyncGenerator[Redis]:
    """Attach a clean test Redis client to the app state, mirroring what the lifespan does on startup."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=15,  # Use separate DB for tests
        decode_responses=True,
    )

    await client.ping()
    await client.flushdb()

    setattr(main_app.state, IN_STATE_NAME, client)

    yield client

    delattr(main_app.state, IN_STATE_NAME)

    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture
async def app_client() -> AsyncGenerator[AsyncClient]:
    """Drive the ASGI app in the running test event loop, so it shares the loop with the Redis fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=main_app),
        base_url=SERVER_URL,
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def _no_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the background task from hitting a real SMTP server."""

    async def _fake_send_email(*_args: object, **_kwargs: object) -> None:
        return

    monkeypatch.setattr(password.NOTIFICATION_SENDER, "send_email", _fake_send_email)


@pytest.fixture(autouse=False)
def _account_exists(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Simulate the existence of an account.

    Return values are taken from the ``account_exists`` marker, e.g.
    ``@pytest.mark.account_exists(email=False, alias=True)``. Defaults to ``(True, True)``.

    """
    marker = request.node.get_closest_marker("account_exists")
    email_exists = marker.kwargs.get("email", True) if marker else True
    alias_exists = marker.kwargs.get("alias", True) if marker else True

    async def _mock(*_args: object, **_kwargs: object) -> tuple[bool, bool]:
        return email_exists, alias_exists

    monkeypatch.setattr(password, "account_exists", _mock)


async def find_keys(redis_client: Redis, pattern: str, count: int = 10) -> list[str]:
    return [key async for key in redis_client.scan_iter(match=pattern, count=count)]


# ======================================================================================================================
# GET ROUTE
# ======================================================================================================================
async def test_get_password_route_as_authenticated_user(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/password route as an authenticated user.

    This test checks if the route returns a 403 Forbidden response when accessed by an authenticated user,
    as they should not be able to request a forgotten password while logged in.
    """
    app_client.cookies.set(AccessToken.cookies_name, str(TEST_ACCESS_TOKEN))
    app_client.cookies.set(RefreshToken.cookies_name, str(TEST_REFRESH_TOKEN))

    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    assert response.status_code == 403
    assert "You are already logged in." in response.content.decode("utf-8")


@pytest.mark.usefixtures("_account_exists")
@pytest.mark.account_exists(email=True, alias=True)
async def test_get_all_valid(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the GET /forgotten_password/password reset route.

    This test checks if the route returns a successful response and contains the expected content.

    """
    # Create a faksimili session in Redis, that would be created at POST /forgotten_password/email
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL})

    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    assert response.status_code == 200
    assert 'input type="password" id="password" name="password"' in response.text
    assert 'input type="password" id="confirm_password" name="confirm_password"' in response.text


async def test_get_missing_session(app_client: AsyncClient) -> None:
    """Test the GET /forgotten_password/password reset route.

    This test checks if the route returns a 400 Bad Request response when the session is missing.

    """
    # Do not create a faksimili session in Redis to simulate a missing session
    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    assert response.status_code == 400
    assert "Invalid or expired forgotten password token" in response.text


async def test_get_invalid_session_state(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the GET /forgotten_password/password reset route with an invalid session state.

    This test checks if the route returns a 400 Bad Request response when the session state is invalid.

    """
    # Create a faksimili session in Redis with an invalid state
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": "not_the_test_email"})

    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    assert response.status_code == 400
    assert "Invalid or expired forgotten password token" in response.text


@pytest.mark.usefixtures("_account_exists")
@pytest.mark.account_exists(email=False, alias=False)
async def test_get_deleted_account(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the GET /forgotten_password/password reset route for a deleted account.

    This test checks if the route returns a successful response and contains the expected content,
    even if the account associated with the email has been deleted.

    """
    # Create a faksimili session in Redis, that would be created at POST /forgotten_password/email
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL})

    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    # Test that user is redirected to the home page
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # Test that the session has been removed from Redis
    assert await redis_client.exists(TEST_SESSION_KEY) == 0


# ======================================================================================================================
# POST ROUTE
# ======================================================================================================================
async def test_post_password_route_as_authenticated_user(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/password route as an authenticated user.

    This test checks if the route returns a 403 Forbidden response when accessed by an authenticated user,
    as they should not be able to request a forgotten password while logged in.
    """
    app_client.cookies.set(AccessToken.cookies_name, str(TEST_ACCESS_TOKEN))
    app_client.cookies.set(RefreshToken.cookies_name, str(TEST_REFRESH_TOKEN))
    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    response = await app_client.post(f"{BASE_URL}/")

    assert response.status_code == 403
    assert "You are already logged in." in response.content.decode("utf-8")


@pytest.mark.usefixtures("_account_exists")
@pytest.mark.account_exists(email=True, alias=True)
async def test_post_all_valid(app_client: AsyncClient, redis_client: Redis) -> None:
    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Create a faksimili session in Redis, that would be created at GET /forgotten_password/password
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    response = await app_client.post(
        f"{BASE_URL}/", data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    assert "Your password has been successfully reset" in response.text
