"""Common Redis functions and utilities for the application."""

from logging import getLogger

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.jwt.access_token import AccessToken
from app.core.jwt.refresh_token import RefreshToken
from app.core.redis.config import REDIS_SETTINGS

LOGGER = getLogger("uvicorn.error")


REDIS_TOKEN_BLACKLIST_KEY_TEMPLATE = "refresh_token:blacklist:%(token_id)s"  # noqa: S105
"""Redis key template for blacklisting refresh tokens."""

REDIS_TOKEN_BLACKLIST_EXPIRATION = AccessToken.time_to_live + 1
"""
Expiration time in seconds for blacklisted refresh tokens in Redis. Set to the access token's TTL plus 1 second
to ensure that token is removed after the access token expires.
"""

REDIS_TOKEN_BLACKLIST_VALUE = "blacklisted"  # noqa: S105
"""Value to store in Redis for blacklisted refresh tokens."""


async def blacklist_refresh_token(token: RefreshToken, redis: Redis) -> bool:
    """Blacklist a refresh token in Redis.

    Args:
        token (RefreshToken): The refresh token to blacklist.
        redis (Redis): The Redis client.

    Returns:
        bool: True if the refresh token was successfully blacklisted, False otherwise.

    """
    result = await redis.set(
        name=REDIS_TOKEN_BLACKLIST_KEY_TEMPLATE % {"token_id": token.token_id},
        value=REDIS_TOKEN_BLACKLIST_VALUE,
        ex=REDIS_TOKEN_BLACKLIST_EXPIRATION,
    )

    return result is True  # redis.set returns True if the operation was successful


async def is_refresh_token_blacklisted(token: RefreshToken, redis: Redis) -> bool:
    """Check if a refresh token is blacklisted in Redis.

    Args:
        token (RefreshToken): The refresh token to check.
        redis (Redis): The Redis client.

    Returns:
        bool: True if the refresh token is blacklisted, False otherwise.

    """
    result = await redis.get(name=REDIS_TOKEN_BLACKLIST_KEY_TEMPLATE % {"token_id": token.token_id})

    # NOTE: "get" returns None if the key does not exist, and the string "blacklisted" if it does.
    return result == REDIS_TOKEN_BLACKLIST_VALUE


def build_redis_key(*args: str) -> str:
    """Build a Redis key by joining the provided arguments with colons.

    Args:
        *args (str): Components of the Redis key.

    Returns:
        str: The constructed Redis key.

    """
    return ":".join(args)


async def open_redis_connection_pool() -> Redis | None:
    """Open a Redis connection pool.

    Returns:
        Redis | None: The Redis client instance, or None if the connection could not be established.

    """
    try:
        pool = ConnectionPool(
            host=REDIS_SETTINGS.host,
            port=REDIS_SETTINGS.port,
            max_connections=20,
            decode_responses=True,  # str in/out instead of bytes
            health_check_interval=30,
        )
        client = Redis(connection_pool=pool)

        # fail fast if unreachable
        await client.ping()

    except RedisError:
        LOGGER.exception("Unable to connect to Redis")

        return None

    else:
        return client


async def close_redis_connection_pool(client: Redis) -> None:
    """Close the Redis connection pool.

    Args:
        client (Redis): The Redis client instance.

    """
    try:
        await client.aclose()

    except RedisError:
        LOGGER.exception("Unable to close Redis connection")


async def hash_object_exists(
    redis_client: Redis,
    key: str,
) -> bool:
    """Check if a hash exists in Redis.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key for the hash.

    Returns:
        bool: True if the hash exists, False otherwise.

    """
    try:
        return await redis_client.exists(key) > 0

    except RedisError:
        LOGGER.exception("Error checking if hash exists for key %s", key)

        return False


async def create_hash_object(
    redis_client: Redis,
    key: str,
    mapping: dict,
    expire_seconds: int,
) -> bool:
    """Set a hash in Redis with an expiration time.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key for the hash.
        mapping (dict): The dictionary to store as a hash.
        expire_seconds (int | None): The expiration time in seconds. If None, the expiration is not set.

    Returns:
        bool: True if the hash was set successfully, False otherwise.

    """
    try:
        async with redis_client.pipeline(transaction=True) as connection:
            connection.hset(key, mapping=mapping)
            connection.expire(key, expire_seconds)

            # Execute the pipeline and check if the hash was set successfully
            results = await connection.execute()

            return all(result > 0 for result in results)

    except RedisError:
        LOGGER.exception("Create hash object failed for key %s", key)

        return False


async def update_hash_object(
    redis_client: Redis,
    key: str,
    mapping: dict,
    expire_seconds: int | None = None,
) -> bool:
    """Update a hash in Redis with an optional expiration time.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key for the hash.
        mapping (dict): The dictionary to update as a hash.
        expire_seconds (int | None): The expiration time in seconds. If None, the expiration is not updated.

    Returns:
        bool: True if the hash was updated successfully, False otherwise.

    """
    try:
        async with redis_client.pipeline(transaction=True) as connection:
            connection.hset(key, mapping=mapping)

            if expire_seconds is not None:
                connection.expire(key, expire_seconds)

            # Execute the pipeline and check if the hash was updated successfully
            results = await connection.execute()

            return all(result > 0 for result in results)

    except RedisError:
        LOGGER.exception("Update hash object failed for key %s", key)

        return False


async def increment_hash_field(
    redis_client: Redis,
    key: str,
    field: str,
    amount: int = 1,
    expire_seconds: int | None = None,
) -> bool:
    """Increment a specific field in a hash stored in Redis.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key for the hash.
        field (str): The field to increment.
        amount (int): The amount to increment by. Defaults to 1.
        expire_seconds (int | None): The expiration time in seconds. If None, the expiration is not updated.

    Returns:
        bool: True if the field was incremented successfully, False if the key does not exist
            or an error occurred.

    """
    try:
        async with redis_client.pipeline(transaction=True) as connection:
            # Add key validation to ensure the key exists before incrementing the field
            connection.exists(key)

            # Increment the specified field in the hash by the given amount
            connection.hincrby(key, field, amount)

            if expire_seconds is not None:
                connection.expire(key, expire_seconds)

            # Execute the pipeline and check if the hash was updated successfully
            results = await connection.execute()

            if results[0] == 0:
                # The key did not exist, so HINCRBY created it as a side effect (without a TTL).
                # Remove it to avoid leaving an orphaned key behind, and report failure.
                await redis_client.delete(key)

                return False

            return all(result > 0 for result in results[1:])

    except RedisError:
        LOGGER.exception("Increment hash field failed for key %s", key)

        return False


async def regenerate_hash_object(
    redis_client: Redis,
    old_session_key: str,
    new_session_key: str,
    mapping: dict,
    expire_seconds: int,
) -> bool:
    """Regenerate a hash in Redis by creating a new hash with the provided mapping and deleting the old hash.

    Even though this is sub-optimal for performance, it will be used

    Args:
        redis_client (Redis): The Redis client instance.
        old_session_key (str): The key for the old hash.
        new_session_key (str): The key for the new hash.
        mapping (dict): The dictionary to set as the new hash.
        expire_seconds (int): The expiration time in seconds for the new hash.

    Returns:
        bool: True if the hash was regenerated successfully, False otherwise.

    """
    try:
        async with redis_client.pipeline(transaction=True) as connection:
            # Set the new hash with the provided mapping and expiration time
            connection.hset(new_session_key, mapping=mapping)
            connection.expire(new_session_key, expire_seconds)

            # Delete the old hash to prevent replay attacks
            connection.delete(old_session_key)

            # Execute the pipeline and check if the hash was set successfully
            results = await connection.execute()

            # Exclude the result of the delete operation from the success check
            return all(result > 0 for result in results[:-1])

    except RedisError:
        LOGGER.exception(
            "Regenerate hash object failed for old key %s and new key %s", old_session_key, new_session_key
        )

        return False


async def get_hash_object(
    redis_client: Redis,
    key: str,
) -> dict | None:
    """Get a hash from Redis.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key for the hash.

    Returns:
        dict | None: The hash stored in Redis, or None if the key does not exist.

    """
    try:
        result = await redis_client.hgetall(key)

    except RedisError:
        LOGGER.exception("Error getting hash object for key %s", key)

        return None

    else:
        return result if result else None


async def delete_object(
    redis_client: Redis,
    key: str,
) -> bool:
    """Delete a key from Redis.

    Args:
        redis_client (Redis): The Redis client instance.
        key (str): The key to delete.

    Returns:
        bool: True if the key was deleted successfully, False otherwise.

    """
    try:
        return await redis_client.delete(key) > 0

    except RedisError:
        LOGGER.exception("Error deleting key %s", key)

        return False
