"""Redis based IP and email limiter for sensitive endpoint call attempts."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis


EMAIL_ATTEMPT_KEY_TEMPLATE = "%(prefix)s:attempts:email:%(email)s"
"""Redis key template for tracking email-based attempts."""

IP_ATTEMPT_KEY_TEMPLATE = "%(prefix)s:attempts:ip:%(ip)s"
"""Redis key template for tracking IP-based attempts."""

ATTEMPTS_LIMIT = 3
"""Maximum number of allowed attempts before lockout."""


async def add_access_attempt(
    prefix: str,
    email: str,
    ip: str,
    redis: Redis,
    ttl: int = 3600,
    limit: int = ATTEMPTS_LIMIT,
) -> bool:
    """Add an endpoint call attempt for the given email and IP in Redis.

    Args:
        prefix (str): The prefix to use for the Redis keys.
        ip (str): The IP address to track attempts for.
        email (str): The email address to track attempts for.
        redis (Redis): The Redis client.
        ttl (int, optional): The time-to-live for the attempt keys in seconds. Defaults to 3600.
        limit (int, optional): The maximum number of allowed attempts. Defaults to 3.

    Returns:
        bool: True if the number of attempts is within the limit, False if the limit has been exceeded.

    """
    email_key = EMAIL_ATTEMPT_KEY_TEMPLATE % {"prefix": prefix, "email": email}
    ip_key = IP_ATTEMPT_KEY_TEMPLATE % {"prefix": prefix, "ip": ip}

    # Use a Redis pipeline to increment the attempt count and set the expiration in a single atomic operation.
    async with redis.pipeline(transaction=True) as connection:
        # Add/increment the attempt count
        connection.incr(email_key)
        connection.incr(ip_key)

        # Set the expiration for the key to lock out further attempts after the limit is reached
        # Each time an attempt is made, the expiration is reset to ensure that the lockout duration
        # is enforced from the last attempt.
        connection.expire(email_key, ttl)
        connection.expire(ip_key, ttl)

        email_attempts, ip_attempts, _, _ = await connection.execute()

        return email_attempts <= limit and ip_attempts <= limit


async def reset_access_attempt(prefix: str, email: str, ip: str, redis: Redis) -> bool:
    """Reset the attempts for the given email and IP in Redis.

    Args:
        prefix (str): The prefix to use for the Redis keys.
        email (str): The email address to reset attempts for.
        ip (str): The IP address to reset attempts for.
        redis (Redis): The Redis client.

    Returns:
        bool: True if the attempts were reset successfully, False if there was an error.

    """
    async with redis.pipeline(transaction=True) as connection:
        connection.delete(EMAIL_ATTEMPT_KEY_TEMPLATE % {"prefix": prefix, "email": email})
        connection.delete(IP_ATTEMPT_KEY_TEMPLATE % {"prefix": prefix, "ip": ip})

        return all(await connection.execute())
