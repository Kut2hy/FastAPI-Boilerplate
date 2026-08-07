"""PostgreSQL connection and pool settings."""

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.app_config import APP_SETTINGS


class PGConnectionSettings(BaseSettings):
    """Pydantic environment settings for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POSTGRES_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )

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


class PGPoolSettings(BaseSettings):
    """Pydantic environment settings for the connection pool."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POOL_POSTGRES_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )

    max_connections: int = Field(default=100, ge=1)
    """Maximum number of connections in the pool. Keep ``workers * pool_max_size`` below "SHOW max_connections;"."""

    max_queries: int = Field(default=10_000, ge=1)
    """Queries a single connection serves before it is recycled."""

    max_inactive_connection_lifetime: float = Field(default=300.0, ge=0)
    """Seconds an idle connection is kept. Also reaps connections dropped by a proxy."""

    @computed_field
    @property
    def min_size(self) -> int:
        """Lower bound of pooled connections."""
        return min(int(self.max_size * 0.2), 5)

    @computed_field
    @property
    def max_size(self) -> int:
        """Upper bound of pooled connections."""
        return max(self.max_connections // APP_SETTINGS.num_workers, 1)


POSTGRES_CON_SETTINGS: PGConnectionSettings = PGConnectionSettings.model_validate({})
"""Instance of the PGConnectionSettings class containing the validated environment settings."""

POSTGRES_POOL_SETTINGS: PGPoolSettings = PGPoolSettings.model_validate({})
"""Instance of the PGPoolSettings class containing the validated environment settings."""
