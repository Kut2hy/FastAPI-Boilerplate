"""Functions to manage the PostgreSQL database connection pool."""

from logging import getLogger

from asyncpg import PostgresError
from piccolo.engine import engine_finder
from piccolo.engine.postgres import PostgresEngine

from app.piccolo.pg_config import POSTGRES_POOL_SETTINGS

_LOGGER = getLogger("piccolo.pool")
"""Logger for the database connection pool."""


async def open_database_connection_pool() -> None:
    """Start the connection pool of the Piccolo engine declared in ``piccolo_conf.py``."""
    engine = engine_finder()

    if not isinstance(engine, PostgresEngine):
        _LOGGER.warning("No PostgresEngine found - skipping connection pool startup.")
        return

    try:
        await engine.start_connection_pool(
            **{
                key: value
                for key, value in POSTGRES_POOL_SETTINGS.model_dump().items()
                if key not in ("max_connections",)
            }
        )

    except OSError, PostgresError:
        _LOGGER.exception("Unable to open the database connection pool: %s")

    else:
        _LOGGER.info("Database connection pool opened.")


async def close_database_connection_pool() -> None:
    """Close the connection pool of the Piccolo engine declared in ``piccolo_conf.py``."""
    engine = engine_finder()

    if not isinstance(engine, PostgresEngine):
        _LOGGER.warning("No PostgresEngine found - skipping connection pool shutdown.")
        return

    try:
        await engine.close_connection_pool()

    except OSError, PostgresError:
        _LOGGER.exception("Error while closing the database connection pool.")

    else:
        _LOGGER.info("Database connection pool closed.")
