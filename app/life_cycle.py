"""Context manager defining the life cycle of the application, including startup and shutdown procedures."""

import logging
import logging.handlers
from contextlib import asynccontextmanager
from logging import getLogger
from typing import TYPE_CHECKING

from app.core.redis.dependencies import IN_STATE_NAME
from app.core.redis.functions import close_redis_connection_pool, open_redis_connection_pool
from app.piccolo.pool import close_database_connection_pool, open_database_connection_pool

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI
    from redis.asyncio import Redis


@asynccontextmanager
async def life_cycle(app: FastAPI) -> AsyncGenerator[None]:
    """Define the life cycle of the application, including startup and shutdown procedures."""

    # ==========================================================================================
    # Non-blocking logging setup.
    # ==========================================================================================

    # Python 3.13: dictConfig creates QueueListeners but does not start them.
    # Start all un-started listeners now, after uvicorn has applied its log_config.
    _active_listeners = []

    # Accessing the internal _handlers dictionary to get all handlers, including those created by dictConfig.
    # Suppressing type checking for _handlers as it is an internal attribute and may not be recognized by type checkers.
    _startup_listeners = list(logging._handlers.values())  # pyright: ignore[reportAttributeAccessIssue] # noqa: SLF001

    for handler in _startup_listeners:
        if isinstance(handler, logging.handlers.QueueHandler) and hasattr(handler, "listener"):
            listener: logging.handlers.QueueListener | None = handler.listener

            # Suppressing private attribute access for _thread as it is an internal attribute of QueueListener,
            # but we need to check if the listener thread is alive before starting it to avoid RuntimeError.
            if listener and not (listener._thread and listener._thread.is_alive()):  # noqa: SLF001
                listener.start()
                _active_listeners.append(listener)

    logger: logging.Logger = getLogger("uvicorn")

    logger.info("==== Starting application ".ljust(80, "="))

    # ==========================================================================================
    # Pre startup procedures can be added below this breakpoint.
    # ==========================================================================================
    await open_database_connection_pool()

    redis_client: Redis | None = await open_redis_connection_pool()
    if not redis_client:
        raise RuntimeError("Failed to establish Redis connection during startup procedures.")

    # Attach the Redis client to the FastAPI app state
    setattr(app.state, IN_STATE_NAME, redis_client)

    # ==========================================================================================
    # Pre startup procedures can be added above this breakpoint.
    # ==========================================================================================
    logger.info("==== Application startup complete ".ljust(80, "="))

    yield  # Yield control back to the FastAPI, waiting for interruptions or shutdown signals.

    logger.info("==== Stopping application ".ljust(80, "="))
    # ==========================================================================================
    # Post shutdown procedures can be added below this breakpoint.
    # ==========================================================================================
    await close_database_connection_pool()
    await close_redis_connection_pool(redis_client)

    # ==========================================================================================
    # Post shutdown procedures can be added above this breakpoint.
    # ==========================================================================================
    logger.info("==== Application has been stopped ".ljust(80, "="))

    for listener in _active_listeners:
        if listener:
            listener.stop()

    # ==========================================================================================
    # All teardown procedures are complete.
    # ==========================================================================================
