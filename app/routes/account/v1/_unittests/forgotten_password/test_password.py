"""Test suite for the password module in the forgotten password feature of the account v1 routes."""

from typing import TYPE_CHECKING
from uuid import uuid7

import pytest
import pytest_asyncio
from piccolo.testing.model_builder import ModelBuilder

from app.core.jwt.access_token import AccessToken
from app.core.jwt.refresh_token import RefreshToken
from app.core.password import hash_password, verify_password
from app.core.redis.session import SESSION_KEY_TEMPLATE
from app.piccolo.tables.user_account import UserAccount
from app.routes.account.v1.forgotten_password import email, password
from app.routes.account.v1.forgotten_password.__constants import FORGOTTEN_PASSW_COOKIE_NAME

if TYPE_CHECKING:
    from httpx import AsyncClient
    from redis.asyncio import Redis

pytestmark = pytest.mark.asyncio(loop_scope="session")

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


@pytest_asyncio.fixture(loop_scope="session")
async def test_account(db_transaction: object) -> UserAccount:
    """Seed the test user into the transactional test database, rolled back after each test."""
    return await ModelBuilder.build(
        UserAccount,
        minimal=True,
        defaults={
            "id": TEST_USER_UUID,
            "email": TEST_EMAIL,
            "user_alias": "test_user",
            "was_email_verified": True,
            "password_hash": hash_password("DefaultPassword123!"),
        },
    )


@pytest.fixture(autouse=True)
def _no_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the background task from hitting a real SMTP server."""

    async def _fake_send_email(*_args: object, **_kwargs: object) -> None:
        return

    monkeypatch.setattr(password.NOTIFICATION_SENDER, "send_email", _fake_send_email)


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


@pytest.mark.usefixtures("test_account")
async def test_get_all_valid(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the GET /forgotten_password/password reset route.

    This test checks if the route returns a successful response and contains the expected content.

    """
    # Create a faksimili session in Redis, that would be created at POST /forgotten_password/email
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL})

    response = await app_client.get(f"{BASE_URL}/?token={TEST_URL_TOKEN}")

    # Test HTML response for the password reset page
    assert response.status_code == 200
    assert 'input type="password" id="password" name="password"' in response.text
    assert 'input type="password" id="confirm_password" name="confirm_password"' in response.text

    # Test cookies for the session token
    assert FORGOTTEN_PASSW_COOKIE_NAME in app_client.cookies

    # Test that the session exists in Redis
    session_result = await find_keys(
        redis_client, SESSION_KEY_TEMPLATE % {"prefix": password.FORGOTTEN_PASSW_PREFIX, "url_token": "*"}
    )

    # Test that a session key is created in Redis for the forgotten password process
    assert session_result


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


@pytest.mark.usefixtures("db_transaction")
async def test_get_deleted_account(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the GET /forgotten_password/password reset route for a deleted account.

    The account has been deleted, so the route should handle this scenario gracefully.

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


@pytest.mark.usefixtures("test_account")
async def test_post_all_valid(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the POST /forgotten_password/password route with all valid inputs."""
    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Create a faksimili session in Redis, that would be created at GET /forgotten_password/password
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    account = await UserAccount.objects().where(UserAccount.email == TEST_EMAIL).first()
    assert account is not None

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
    )

    # Tests HTML response for successful password reset
    assert response.status_code == 200
    assert "Your password has been successfully reset" in response.text

    # Tests that the account's password has been updated correctly
    await account.refresh()
    assert verify_password(TEST_PASSWORD, account.password_hash)

    # Tests that the Redis session has been removed after successful password reset
    assert await redis_client.exists(TEST_SESSION_KEY) == 0


async def test_post_missing_cookie(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/password reset route when the forgotten password cookie is missing."""

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
    )

    assert response.status_code == 400
    assert "Invalid or expired forgotten password token" in response.text


async def test_post_missing_session(app_client: AsyncClient) -> None:
    """Test the POST /forgotten_password/password reset route when the session is missing."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
    )

    assert response.status_code == 400
    assert "Invalid or expired forgotten password token" in response.text


async def test_post_invalid_session_state(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the POST /forgotten_password/password reset route when the Redis session is in an invalid state."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Redis session is missing the expected "valid" field. AKA somehow skipping GET step
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL})

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
    )

    assert response.status_code == 400
    assert "Invalid or expired forgotten password token" in response.text


@pytest.mark.usefixtures("db_transaction")
async def test_post_deleted_account(app_client: AsyncClient, redis_client: Redis) -> None:
    """Test the POST /forgotten_password/password reset route when the account has been deleted."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Redis session is valid
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": TEST_PASSWORD, "confirm_password": TEST_PASSWORD},
    )

    assert response.status_code == 400
    assert "Failed to change password." in response.text


@pytest.mark.parametrize(
    "form_data",
    [
        ({"password": TEST_PASSWORD}),
        ({"confirm_password": TEST_PASSWORD}),
    ],
)
async def test_post_missing_password(app_client: AsyncClient, redis_client: Redis, form_data: dict) -> None:
    """Test the POST /forgotten_password/password reset route when the password is missing."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Redis session is valid
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    response = await app_client.post(f"{BASE_URL}/", data=form_data)

    assert response.status_code == 422
    assert "Both password and confirm_password must be provided" in response.text


@pytest.mark.parametrize(
    ("password", "confirm_password", "error_message"),
    [
        (TEST_PASSWORD, "B@dConfirmPa33", "Passwords do not match."),
        ("B@dConfirmPa33", TEST_PASSWORD, "Passwords do not match."),
    ],
)
async def test_post_password_mismatch(
    app_client: AsyncClient,
    redis_client: Redis,
    password: str,
    confirm_password: str,
    error_message: str,
) -> None:
    """Test the POST /forgotten_password/password reset route when the passwords do not match."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Redis session is valid
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": password, "confirm_password": confirm_password},
    )

    assert response.status_code == 422
    assert error_message in response.text


@pytest.mark.parametrize(
    ("password", "confirm_password", "error_message"),
    [
        ("", "", "Password does not match the required pattern."),
        ("short", "short", "Password does not match the required pattern."),
        ("NoSpecialChar123", "NoSpecialChar123", "Password does not match the required pattern."),
        ("nouppercase123!", "nouppercase123!", "Password does not match the required pattern."),
        ("NOLOWERCASE123!", "NOLOWERCASE123!", "Password does not match the required pattern."),
    ],
)
async def test_post_invalid_password_patterns(
    app_client: AsyncClient,
    redis_client: Redis,
    password: str,
    confirm_password: str,
    error_message: str,
) -> None:
    """Test the POST /forgotten_password/password reset route with various invalid password patterns."""

    app_client.cookies.set(FORGOTTEN_PASSW_COOKIE_NAME, TEST_URL_TOKEN)

    # Redis session is valid
    await redis_client.hset(TEST_SESSION_KEY, mapping={"email": TEST_EMAIL, "valid": "true"})

    response = await app_client.post(
        f"{BASE_URL}/",
        data={"password": password, "confirm_password": confirm_password},
    )

    assert response.status_code == 422
    assert error_message in response.text
