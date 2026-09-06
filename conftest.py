"""Global pytest fixtures for the Piccolo test database.

Two ordering constraints drive the layout of this module:

1. ``PICCOLO_CONF`` must be set before anything imports ``app.piccolo.tables.*``, because
   ``Table.__init_subclass__`` resolves its engine through ``engine_finder()`` at class creation time.
2. The test database must already exist at collection time, because ``PostgresEngine.__init__``
   connects eagerly to check the server version.

Hence the database itself is created in ``pytest_sessionstart``, while everything a test consumes
(``db_schema``, ``db_transaction``) is an ordinary fixture.
"""

import asyncio
import os
import re
from typing import TYPE_CHECKING, Any

os.environ["PICCOLO_CONF"] = "piccolo_conf_test"

import asyncpg
import pytest  # noqa: TC002 - pytest resolves hook annotations at runtime
import pytest_asyncio
from piccolo.conf.apps import Finder
from piccolo.engine import engine_finder
from piccolo.table import Table, create_db_tables, drop_db_tables

from app.piccolo.pg_config import POSTGRES_CON_SETTINGS

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from piccolo.engine.base import Engine
    from piccolo.engine.postgres import PostgresEngine, PostgresTransaction

TEST_DATABASE_NAME = f"test_{POSTGRES_CON_SETTINGS.database}"
"""Name of the throwaway database created and dropped around the test session."""

os.environ["PICCOLO_TEST_DATABASE"] = TEST_DATABASE_NAME

_SAFE_DB_NAME = re.compile(r"^[A-Za-z0-9_]+$")
"""``CREATE DATABASE`` cannot be parameterised, so the name is validated instead of escaped."""

_TEST_POOL_MIN_SIZE = 1
"""Lower bound of pooled connections for the test engine."""

_TEST_POOL_MAX_SIZE = 5
"""Upper bound of pooled connections for the test engine."""


def _test_db_connection_kwargs() -> dict[str, Any]:
    """Build asyncpg kwargs for the ``postgres`` testing database."""
    return {
        "host": POSTGRES_CON_SETTINGS.host,
        "port": POSTGRES_CON_SETTINGS.port,
        "user": POSTGRES_CON_SETTINGS.user.get_secret_value(),
        "password": POSTGRES_CON_SETTINGS.password.get_secret_value(),
        "database": "postgres",
        "timeout": POSTGRES_CON_SETTINGS.timeout,
    }


async def _run_test_db_statement(statement: str) -> None:
    """Run a single statement against the ``postgres`` maintenance database."""
    connection = await asyncpg.connect(**_test_db_connection_kwargs())

    try:
        await connection.execute(statement)

    finally:
        await connection.close()


# NOTE: Hook name should not be changed. Pytest relies on this specific name.
def pytest_sessionstart(session: pytest.Session) -> None:
    """Recreate an empty test database before collection imports the Piccolo engine."""
    if not _SAFE_DB_NAME.match(TEST_DATABASE_NAME):
        raise ValueError(f"Unsafe test database name: {TEST_DATABASE_NAME!r}")

    # WITH (FORCE) disconnects clients left over from an aborted run - PostgreSQL 13+.
    asyncio.run(_run_test_db_statement(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)'))
    asyncio.run(_run_test_db_statement(f'CREATE DATABASE "{TEST_DATABASE_NAME}"'))


# NOTE: Hook name should not be changed. Pytest relies on this specific name.
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Drop the test database once every fixture has been finalized."""
    asyncio.run(_run_test_db_statement(f'DROP DATABASE IF EXISTS "{TEST_DATABASE_NAME}" WITH (FORCE)'))


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_database() -> AsyncGenerator[Engine]:
    """Start the Piccolo connection pool against the test database for the whole session."""
    engine: PostgresEngine | None = engine_finder() # type: ignore

    if engine is None:
        raise RuntimeError("No Piccolo engine found")

    await engine.start_connection_pool(min_size=_TEST_POOL_MIN_SIZE, max_size=_TEST_POOL_MAX_SIZE)

    try:
        yield engine

    finally:
        await engine.close_connection_pool()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_schema(test_database: Engine) -> AsyncGenerator[list[type[Table]]]:
    """Create every table registered in ``APP_REGISTRY`` once per session and drop them at the end."""
    tables: list[type[Table]] = Finder().get_table_classes()

    await create_db_tables(*tables, if_not_exists=True)

    try:
        yield tables

    finally:
        await drop_db_tables(*tables)


@pytest_asyncio.fixture(loop_scope="session")
async def db_transaction(db_schema: list[type[Table]]) -> AsyncGenerator[PostgresTransaction]:
    """Wrap a single test in a transaction that is always rolled back, so tests never see each other's rows."""
    engine: PostgresEngine | None = engine_finder() # type: ignore

    if engine is None:
        raise RuntimeError("No Piccolo engine found")

    transaction = engine.transaction()

    await transaction.__aenter__()

    try:
        yield transaction

    finally:
        await transaction.rollback()
        await transaction.__aexit__(None, None, None)
