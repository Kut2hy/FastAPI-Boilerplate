"""Test suite for the email module in the forgotten password feature of the account v1 routes."""

from typing import TYPE_CHECKING
from uuid import uuid7

import pytest

from app.core.jwt.access_token import AccessToken
from app.core.jwt.refresh_token import RefreshToken
from app.core.redis.limiter import ATTEMPTS_LIMIT
from app.core.redis.session import SESSION_KEY_TEMPLATE
from app.routes.account.v1.forgotten_password import email
from app.routes.account.v1.forgotten_password.__constants import FORGOTTEN_PASSW_COOKIE_NAME

if TYPE_CHECKING:
    from httpx import AsyncClient
    from redis.asyncio import Redis

pytestmark = pytest.mark.asyncio(loop_scope="session")

BASE_URL = email.FORGOTTEN_PASSW_URL + f"/{email.CURRENT_ENDPOINT}"
"""Base URL for the forgotten password email route being tested."""

TEST_USER_UUID = uuid7()
"""UUID for a test user, used in generating tokens for authenticated requests."""

TEST_ACCESS_TOKEN = AccessToken.generate_token(subject=TEST_USER_UUID, alias="test_user", roles="")
"""Access token for the test user, used in authenticated requests."""

TEST_REFRESH_TOKEN = RefreshToken.generate_token(subject=TEST_USER_UUID)
"""Refresh token for the test user, used in authenticated requests."""


@pytest.fixture(autouse=True)
def _no_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the background task from hitting a real SMTP server."""

    async def _fake_send_email(*_args: object, **_kwargs: object) -> None:
        return

    monkeypatch.setattr(email.FORGOTTEN_PASSW_NOTIFICATION_SENDER, "send_email", _fake_send_email)


async def find_keys(redis_client: Redis, pattern: str, count: int = 10) -> list[str]:
    return [key async for key in redis_client.scan_iter(match=pattern, count=count)]


# ======================================================================================================================
# GET ROUTE
# ======================================================================================================================
async def test_get_email_route(app_client: AsyncClient) -> None:
    """Test the GET /forgotten_password/email route.

    This test checks if the route returns a successful response and contains the expected content.

    """
    response = await app_client.get(f"{BASE_URL}/")

    assert response.status_code == 200
    assert "Forgotten Password" in response.text


async def test_get_email_route_as_authenticated_user(app_client: AsyncClient) -> None:
    """Test the GET /forgotten_password/email route as an authenticated user.

    This test checks if the route returns a 403 Forbidden response when accessed by an authenticated user,
    as they should not be able to request a forgotten password while logged in.
    """
    app_client.cookies.set(AccessToken.cookies_name, str(TEST_ACCESS_TOKEN))
    app_client.cookies.set(RefreshToken.cookies_name, str(TEST_REFRESH_TOKEN))

    response = await app_client.get(f"{BASE_URL}/")

    assert response.status_code == 403
    assert "You are already logged in." in response.content.decode("utf-8")


# ======================================================================================================================
# POST ROUTE
# ======================================================================================================================
async def test_post_email_route(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the POST /forgotten_password/email route.

    This test checks if the route returns a successful response when a valid email is submitted.

    """
    test_email = "test@example.com"
    test_ip = "127.0.0.1"

    form_data = {"email": test_email}
    response = await app_client.post(f"{BASE_URL}/", data=form_data)

    # Test that the response is successful and contains the expected message
    assert response.status_code == 200
    assert "Please check your email for further instructions to reset your password." in response.text

    # Test that attempts limiter keys are set in Redis
    assert await redis_client.exists(f"{email.FORGOTTEN_PASSW_PREFIX}:attempts:email:{test_email}") == 1
    assert await redis_client.exists(f"{email.FORGOTTEN_PASSW_PREFIX}:attempts:ip:{test_ip}") == 1

    session_result = await find_keys(
        redis_client, SESSION_KEY_TEMPLATE % {"prefix": email.FORGOTTEN_PASSW_PREFIX, "url_token": "*"}
    )

    # Test that a session key is created in Redis for the forgotten password process
    assert session_result

    # Test that the session cookie is set in the client
    assert FORGOTTEN_PASSW_COOKIE_NAME in app_client.cookies


async def test_post_email_route_limiter(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/email route with the attempts limiter.

    This test checks if the route returns a 429 Too Many Requests response after exceeding the limit.

    """
    test_email = "test@example.com"
    form_data = {"email": test_email}

    for _ in range(ATTEMPTS_LIMIT):
        response = await app_client.post(f"{BASE_URL}/", data=form_data)
        assert response.status_code == 200

    response = await app_client.post(f"{BASE_URL}/", data=form_data)

    assert response.status_code == 429
    assert "Too many forgotten password attempts" in response.text


async def test_post_email_route_limiter_ip(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/email route with the attempts limiter for IP address.

    In this test, we simulate multiple requests from the same IP address, but attempt to use different email addresses.
    As this test does not change origin IP address of ASGI test client, this can simulate a scenario where an "attacker"
    could be trying to test existence of multiple email addresses.

    """
    test_email = "test%d@example.com"

    for i in range(ATTEMPTS_LIMIT):
        form_data = {"email": test_email % i}
        response = await app_client.post(f"{BASE_URL}/", data=form_data)
        assert response.status_code == 200

    form_data = {"email": test_email % (ATTEMPTS_LIMIT + 1)}
    response = await app_client.post(f"{BASE_URL}/", data=form_data)

    assert response.status_code == 429
    assert "Too many forgotten password attempts" in response.text


async def test_post_email_route_as_authenticated_user(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/email route as an authenticated user.

    This test checks if the route returns a 403 Forbidden response when accessed by an authenticated user,
    as they should not be able to request a forgotten password while logged in.
    """
    app_client.cookies.set(AccessToken.cookies_name, str(TEST_ACCESS_TOKEN))
    app_client.cookies.set(RefreshToken.cookies_name, str(TEST_REFRESH_TOKEN))

    form_data = {"email": "test@example.com"}
    response = await app_client.post(f"{BASE_URL}/", data=form_data)

    assert response.status_code == 403
    assert "You are already logged in." in response.content.decode("utf-8")


async def test_post_email_route_invalid_email(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/email route with an invalid email.

    This test checks if the route returns a successful response even when an invalid email is submitted,
    to prevent user enumeration.

    """
    invalid_email = "invalid-email"
    form_data = {"email": invalid_email}

    result = await app_client.post(f"{BASE_URL}/", data=form_data)

    # Test that "Unprocessable Entity" is returned for invalid email input, indicating that the input validation failed
    assert result.status_code == 422
