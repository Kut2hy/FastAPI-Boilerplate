"""Application/environment configuration settings for the FastAPI application."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Pydantic environment settings for the FastAPI application."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_prefix="APP_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )

    title: Annotated[str, Field(default="FastAPI Application", max_length=100)]
    """The name of the FastAPI application."""

    version: Annotated[str, Field(default="0.1.0", pattern=r"^\d{1,2}\.\d{1,2}\.\d{1,2}$")]
    """The version of the FastAPI application."""

    environment: Annotated[Literal["development", "production"], Field(default="development")]
    """The current environment of the application."""

    host: Annotated[str, Field(default="127.0.0.1")]
    """The host address on which the FastAPI application will run."""

    public_host: Annotated[str | None, Field(default=None, max_length=253)]
    """The public domain the application is served on behind a reverse proxy."""

    port: Annotated[int, Field(default=8000, ge=1, le=65535)]
    """The port number on which the FastAPI application will listen."""

    num_workers: Annotated[int, Field(default=2, ge=1, le=8)]
    """The number of worker processes for the FastAPI application."""

    @computed_field
    @property
    def app_root(self) -> str:
        """Root directory of the application, not of the project."""
        return str(Path(__file__).parent.resolve())

    @computed_field
    @property
    def in_development(self) -> bool:
        """Check if the application is running in development mode."""
        return self.environment == "development"


APP_SETTINGS: AppSettings = AppSettings.model_validate({})
"""Instance of the AppSettings class containing the validated environment settings."""
