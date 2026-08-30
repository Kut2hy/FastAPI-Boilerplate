"""Common constants and functions for the registration routes."""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from app.common.middleware.server_timings import capture_duration

from .__models import (
    AfterAccountInfoState,
    AfterAliasState,
    AfterClickThroughState,
    AfterCreationState,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

ABS_FS_PATH_PARTS = Path(__file__).parent.parts
"""Absolute path parts of the current file's registration directory."""

REGISTRATION_FS_PATH_PARTS = ABS_FS_PATH_PARTS[ABS_FS_PATH_PARTS.index("routes") + 1 :]
"""File system path parts for the registration routes, relative to the 'routes' directory."""

REGISTRATION_FS_PATH = "/".join(REGISTRATION_FS_PATH_PARTS)
"""File system path for the registration routes, relative to the 'routes' directory."""

REGISTRATION_URL = "/" + REGISTRATION_FS_PATH.replace("-", "_")
"""URL path for the registration routes, derived from the file system path."""

REGISTRATION_KEY_TEMPLATE = "registration:%(url_token)s"
"""Redis key template for storing the registration token associated with a user's email."""

REGISTRATION_KEY_TTL = 600
"""Expiration time in seconds for the registration key sent to the user's email."""

REGISTRATION_LOCKOUT_TTL = 3600
"""Expiration time in seconds for the lockout period after exceeding registration attempts."""

REGISTRATION_COOKIE_NAME = "registration_token"
"""Name of the cookie used to store the registration token."""

REGISTRATION_COOKIE_KWARGS = {
    "key": REGISTRATION_COOKIE_NAME,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": REGISTRATION_URL,
}
"""Default keyword arguments for the registration cookie."""


@capture_duration()
async def create_registration(url_token: str, email: str, redis: Redis) -> bool:
    """Create a new registration entry in Redis with the given URL token and mapping.

    Args:
        url_token (str): The unique URL token for the registration.
        email (str): The email address of the user to be stored.
        redis (Redis): The Redis client for storing the registration data.

    Returns:
        bool: True if the registration entry was created successfully, False if it already existed.

    """
    new_key = REGISTRATION_KEY_TEMPLATE % {"url_token": url_token}

    async with redis.pipeline(transaction=True) as connection:
        # Use HSETNX to set the email only if the key does not already exist
        connection.hsetnx(name=new_key, key="email", value=email)
        connection.expire(new_key, REGISTRATION_KEY_TTL)

        _hsetnx, _expire = await connection.execute()

    return all([_hsetnx, _expire])


@capture_duration()
async def update_registration(url_token: str | None, new_url_token: str, mapping: dict, redis: Redis) -> bool:
    """Update an existing registration entry in Redis by renaming the key and updating its mapping.

    Args:
        url_token (str | None): The current URL token for the registration. If None, does nothing.
        new_url_token (str): The new URL token to replace the current one.
        mapping (dict): A dictionary containing updated registration data to be stored.
        redis (Redis): The Redis client for updating the registration data.

    Returns:
        bool: True if both the rename and update operations were successful, False otherwise.

    """
    if url_token is None:
        return False

    old_key = REGISTRATION_KEY_TEMPLATE % {"url_token": url_token}
    new_key = REGISTRATION_KEY_TEMPLATE % {"url_token": new_url_token}

    async with redis.pipeline(transaction=True) as connection:
        connection.rename(old_key, new_key)
        connection.hset(new_key, mapping=mapping)
        connection.expire(new_key, REGISTRATION_KEY_TTL)

        # NOTE: HSET can return 0 if all fields already exist.
        # Instead check the results of the rename and expire operations to determine success.
        _rename, _, _expire = await connection.execute()

    return all([_rename, _expire])


@capture_duration()
async def get_registration(url_token: str | None, redis: Redis) -> dict | None:
    """Retrieve the registration data associated with the given URL token from Redis.

    Args:
        url_token (str | None): The unique URL token for the registration. If None, returns None.
        redis (Redis): The Redis client for retrieving the registration data.

    Returns:
        dict | None: A dictionary containing the registration data if found,
            or None if the URL token is None or not found in Redis.

    """
    if url_token is None:
        return None

    result = await redis.hgetall(REGISTRATION_KEY_TEMPLATE % {"url_token": url_token})

    return result if result else None


@capture_duration()
async def delete_registration(url_token: str | None, redis: Redis) -> bool:
    """Delete the registration entry associated with the given URL token from Redis.

    Args:
        url_token (str | None): The unique URL token for the registration. If None, does nothing.
        redis (Redis): The Redis client for deleting the registration data.

    Returns:
        bool: True if the registration entry was deleted successfully, False if it did not exist.

    """
    if url_token is None:
        return False

    result = await redis.delete(REGISTRATION_KEY_TEMPLATE % {"url_token": url_token})
    return all([result, ])  # Returns True if the key was deleted, False if it did not exist.


CompositeStateModels = AfterCreationState | AfterClickThroughState | AfterAliasState | AfterAccountInfoState


def validate_redis_state[T: CompositeStateModels](
    redis_state: dict | None,
    model_class: type[T],
) -> T | None:
    """Validate the Redis state against the given Pydantic model class.

    Args:
        redis_state (dict | None): The Redis state to validate.
        model_class (type[T]): The Pydantic model class to validate against.

    Returns:
        T | None: The validated model instance if the Redis state is valid according to the model class,
            or None if the Redis state is None or invalid.

    """
    if redis_state is None:
        return None

    try:
        return model_class.model_validate(redis_state)

    except ValidationError:
        return None
