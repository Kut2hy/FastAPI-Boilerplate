"""Redis session management. Used for storing temporary sessions during registration and forgotten password flows."""

from typing import TYPE_CHECKING

from app.common.middleware.server_timings import capture_duration

if TYPE_CHECKING:
    from redis.asyncio import Redis

SESSION_KEY_TEMPLATE = "%(prefix)s:session:%(url_token)s"
"""
Redis key template for storing session data associated with a user's email
during registration or forgotten password flows.
"""

SESSION_KEY_TTL = 600
"""Expiration time in seconds for the session key sent to the user's email."""


@capture_duration()
async def create_session(prefix: str, url_token: str, email: str, redis: Redis, ttl: int = SESSION_KEY_TTL) -> bool:
    """Create a new session entry in Redis with the given URL token and mapping.

    Args:
        prefix (str): The prefix for the Redis key, e.g., "registration".
        url_token (str): The unique URL token for the registration.
        email (str): The email address of the user to be stored.
        redis (Redis): The Redis client for storing the registration data.
        ttl (int): The time-to-live for the session in seconds AKA Redis key expiration time.

    Returns:
        bool: True if the session entry was created successfully, False if it already existed.

    """
    new_key = SESSION_KEY_TEMPLATE % {"prefix": prefix, "url_token": url_token}

    async with redis.pipeline(transaction=True) as connection:
        # Use HSETNX to set the email only if the key does not already exist
        connection.hsetnx(name=new_key, key="email", value=email)
        connection.expire(new_key, ttl)

        _hsetnx, _expire = await connection.execute()

    return all([_hsetnx, _expire])


@capture_duration()
async def update_session(
    prefix: str, url_token: str | None, new_url_token: str, mapping: dict, redis: Redis, ttl: int = SESSION_KEY_TTL
) -> bool:
    """Update an existing session entry in Redis by renaming the key and updating its mapping.

    Args:
        prefix (str): The prefix for the Redis key, e.g., "registration".
        url_token (str | None): The current URL token for the session. If None, does nothing.
        new_url_token (str): The new URL token to replace the current one.
        mapping (dict): A dictionary containing updated session data to be stored.
        redis (Redis): The Redis client for updating the session data.
        ttl (int): The time-to-live for the session in seconds AKA Redis key expiration time.

    Returns:
        bool: True if both the rename and update operations were successful, False otherwise for the session.

    """
    if url_token is None:
        return False

    old_key = SESSION_KEY_TEMPLATE % {"prefix": prefix, "url_token": url_token}
    new_key = SESSION_KEY_TEMPLATE % {"prefix": prefix, "url_token": new_url_token}

    async with redis.pipeline(transaction=True) as connection:
        connection.rename(old_key, new_key)
        connection.hset(new_key, mapping=mapping)
        connection.expire(new_key, ttl)

        # NOTE: HSET can return 0 if all fields already exist.
        # Instead check the results of the rename and expire operations to determine success.
        _rename, _, _expire = await connection.execute()

    return all([_rename, _expire])


@capture_duration()
async def get_session(prefix: str, url_token: str | None, redis: Redis) -> dict | None:
    """Retrieve the session data associated with the given URL token from Redis.

    Args:
        prefix (str): The prefix for the Redis key, e.g., "registration".
        url_token (str | None): The unique URL token for the session. If None, returns None.
        redis (Redis): The Redis client for retrieving the session data.

    Returns:
        dict | None: A dictionary containing the session data if found,
            or None if the URL token is None or not found in Redis.

    """
    if url_token is None:
        return None

    result = await redis.hgetall(SESSION_KEY_TEMPLATE % {"prefix": prefix, "url_token": url_token})

    return result if result else None


@capture_duration()
async def delete_session(prefix: str, url_token: str | None, redis: Redis) -> bool:
    """Delete the session entry associated with the given URL token from Redis.

    Args:
        prefix (str): The prefix for the Redis key, e.g., "registration".
        url_token (str | None): The unique URL token for the session. If None, does nothing.
        redis (Redis): The Redis client for deleting the session data.

    Returns:
        bool: True if the session entry was deleted successfully, False if it did not exist.

    """
    if url_token is None:
        return False

    result = await redis.delete(SESSION_KEY_TEMPLATE % {"prefix": prefix, "url_token": url_token})
    return all(
        [
            result,
        ]
    )  # Returns True if the key was deleted, False if it did not exist.
