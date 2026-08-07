"""PostgreSQL connection and pool settings."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class PGConnectionSettings(BaseSettings):
    """Pydantic environment settings for the application."""

    host: str
    """The hostname or IP address of the PostgreSQL server."""

    port: int = Field(default=5432, ge=1, le=65535)
    """The port number on which the PostgreSQL server is listening."""

    user: SecretStr
    """The username used to authenticate with the PostgreSQL server."""

    password: SecretStr
    """The password used to authenticate with the PostgreSQL server."""

    database: str
    """The name of the PostgreSQL database to connect to."""

    timeout: float = Field(default=10.0, ge=0)
    """Timeout in seconds for establishing a connection to the PostgreSQL server."""

    command_timeout: float = Field(default=10.0, ge=0)
    """Timeout in seconds for executing a command on the PostgreSQL server."""

    statement_cache_size: int = Field(default=100, ge=0)
    """The maximum number of prepared statements to cache per connection."""

    max_cached_statement_lifetime: float = Field(default=60.0 * 10, ge=0)
    """Seconds a cached prepared statement is kept before being re-prepared."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POSTGRES_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )


class PGPoolSettings(BaseSettings):
    """Pydantic environment settings for the connection pool."""

    min_size: int = Field(default=1, ge=1)
    """Lower bound of pooled connections."""

    max_size: int = Field(default=50, ge=1)
    """Upper bound of pooled connections. Keep ``workers * pool_max_size`` below "SHOW max_connections;"."""

    max_queries: int = Field(default=10_000, ge=1)
    """Queries a single connection serves before it is recycled."""

    max_inactive_connection_lifetime: float = Field(default=300.0, ge=0)
    """Seconds an idle connection is kept. Also reaps connections dropped by a proxy."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POOL_POSTGRES_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )


POSTGRES_CON_SETTINGS = PGConnectionSettings.model_validate({})
"""Instance of the PGConnectionSettings class containing the validated environment settings."""

POSTGRES_POOL_SETTINGS = PGPoolSettings.model_validate({})
"""Instance of the PGPoolSettings class containing the validated environment settings."""
