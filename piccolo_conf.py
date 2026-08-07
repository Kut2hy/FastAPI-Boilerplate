"""Piccolo configuration file."""

from app.piccolo.pg_config import POSTGRES_CON_SETTINGS
from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine
from pydantic import SecretStr

DB = PostgresEngine(
    config={
        key: value.get_secret_value() if isinstance(value, SecretStr) else value
        for key, value in POSTGRES_CON_SETTINGS.model_dump().items()
    }
)
"""Piccolo PostgresEngine instance configured with the validated environment settings."""

APP_REGISTRY = AppRegistry(
    apps=[
        "app.piccolo.piccolo_app",
    ]
)
