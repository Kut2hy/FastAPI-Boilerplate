"""Redis based dependencies for the FastAPI application."""

from typing import TYPE_CHECKING

# NOTE: Request must be imported here, as in type checking block Depends will not work properly with it.
from fastapi import Request  # noqa: TC002

from app.core.redis.config import REDIS_SETTINGS

if TYPE_CHECKING:
    from collections.abc import Callable

    from redis.asyncio import Redis

IN_STATE_NAME: str = REDIS_SETTINGS.in_state_name
"""The name of the state variable in the FastAPI app where the Redis client will be stored."""


def get_redis_client() -> Callable[[Request], Redis]:
    """Dependency to get the Redis client from the FastAPI app state.

    Returns:
        Callable[[Request], Redis]: A callable that takes a FastAPI request and returns
            the Redis client instance.

    Raises:
        RuntimeError: If the Redis client is not available in the app state.

    """

    def _getter(request: Request) -> Redis:
        try:
            return request.app.state[IN_STATE_NAME]

        except (AttributeError, KeyError) as exc:
            raise RuntimeError("Redis client is not available in the app state.") from exc

    return _getter
