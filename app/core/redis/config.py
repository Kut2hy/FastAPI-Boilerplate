"""Redis environment settings and configuration for the application."""

from typing import Annotated, Literal

from pydantic import AnyUrl, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


# NOTE: VPS is running:
#   redis_version:8.0.2

class RedisSettings(BaseSettings):
    """Pydantic environment settings for Redis."""

    model_config = SettingsConfigDict(
            frozen=True,
            env_file=".env",
            env_prefix="REDIS_",
            env_file_encoding="utf-8",
            dotenv_filtering="match_prefix",
        )

    host: Annotated[Literal["127.0.0.1", "localhost"] | AnyUrl, Field(default="127.0.0.1")]
    """The host address on which the FastAPI application will run."""

    port: Annotated[int, Field(default=6379, ge=1, le=65535)]
    """The port number on which the FastAPI application will listen."""

    @computed_field
    @property
    def in_state_name(self) -> str:
        """The name of the state variable in the FastAPI app where the Redis client will be stored."""
        return "redis_client"


REDIS_SETTINGS: RedisSettings = RedisSettings.model_validate({})
"""Instance of the RedisSettings class containing the validated environment settings."""
