"""Piccolo configuration used by the test suite.

Selected by exporting ``PICCOLO_CONF=piccolo_conf_test`` before any Piccolo table module is imported,
which the root ``conftest.py`` does for us. Identical to ``piccolo_conf.py`` except that it points at a
throwaway database that is created and dropped by ``conftest.py``.
"""

import os

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
from pydantic import SecretStr

from app.piccolo.pg_config import POSTGRES_CON_SETTINGS

TEST_DATABASE_NAME_ENV_VAR = "PICCOLO_TEST_DATABASE"
"""Environment variable through which ``conftest.py`` hands over the name of the database it created."""

try:
    TEST_DATABASE_NAME = os.environ[TEST_DATABASE_NAME_ENV_VAR]

except KeyError:
    raise RuntimeError(
        f"{TEST_DATABASE_NAME_ENV_VAR} is not set - this config is only meant to be loaded by the test suite."
    ) from None

DB = PostgresEngine(
    config={
        **{
            key: value.get_secret_value() if isinstance(value, SecretStr) else value
            for key, value in POSTGRES_CON_SETTINGS.model_dump().items()
        },
        "database": TEST_DATABASE_NAME,
    }
)
"""Piccolo PostgresEngine instance bound to the test database."""

APP_REGISTRY = AppRegistry(
    apps=[
        "app.piccolo.piccolo_app",
    ]
)
"""Must mirror ``piccolo_conf.APP_REGISTRY`` so ``Finder`` resolves the same table classes."""
