"""Asynchronous logging configuration for FastAPI application using a queue to avoid blocking the main thread."""

from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LoggingSettings(BaseSettings):
    """Pydantic environment settings for logging configuration."""

    level: Literal["debug", "info", "warning", "error", "critical"]
    """The log level for the application."""

    directory: str
    """The directory where log files will be stored."""

    app_file: str = "app.log"
    """The log file name for the application."""

    access_file: str = "access.log"
    """The access log file name for the application."""

    max_bytes: int = 10_485_760
    """The maximum size in bytes of the log file before it is rotated."""

    backup_count: int = 7
    """The number of backup log files to keep."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOGGING_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )

    @computed_field
    @property
    def absolute_directory(self) -> Path:
        """Compute the absolute path of the logging directory."""
        return Path(self.directory).expanduser().resolve()


LOGGING_SETTINGS = LoggingSettings.model_validate({})
"""Instance of the LoggingSettings class containing the validated environment settings."""

if not LOGGING_SETTINGS.absolute_directory.exists():
    LOGGING_SETTINGS.absolute_directory.mkdir(parents=True, exist_ok=True)


LOG_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
        "file_default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "file_access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "use_colors": False,
        },
    },
    "handlers": {
        "stream_default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        },
        "stream_access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": "ext://sys.stdout",
        },
        "file_default": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "file_default",
            "filename": str(LOGGING_SETTINGS.absolute_directory / LOGGING_SETTINGS.app_file),
            "maxBytes": LOGGING_SETTINGS.max_bytes,
            "backupCount": LOGGING_SETTINGS.backup_count,
            "encoding": "utf-8",
        },
        "file_access": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "file_access",
            "filename": str(LOGGING_SETTINGS.absolute_directory / LOGGING_SETTINGS.access_file),
            "maxBytes": LOGGING_SETTINGS.max_bytes,
            "backupCount": LOGGING_SETTINGS.backup_count,
            "encoding": "utf-8",
        },
        "queue_default": {
            "class": "app.core.logging.handlers.PreservingQueueHandler",
            "listener": "logging.handlers.QueueListener",
            "handlers": [
                "stream_default",
                "file_default",
            ],
            "respect_handler_level": True,
        },
        "queue_access": {
            "class": "app.core.logging.handlers.PreservingQueueHandler",
            "listener": "logging.handlers.QueueListener",
            "handlers": [
                "stream_access",
                "file_access",
            ],
            "respect_handler_level": True,
        },
    },
    "loggers": {
        "uvicorn.error": {
            "handlers": ["queue_default"],
            "level": LOGGING_SETTINGS.level.upper(),
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["queue_access"],
            "level": LOGGING_SETTINGS.level.upper(),
            "propagate": False,
        },
        # Explicitly set log levels for specific libraries as they seemingly create blocking behavior.
        "jinjax": {
            "level": LOGGING_SETTINGS.level.upper(),
            "propagate": True,
        },
        "asyncio": {
            "level": LOGGING_SETTINGS.level.upper(),
            "propagate": True,
        },
        "piccolo.engine.base": {
            "level": LOGGING_SETTINGS.level.upper(),
            "propagate": True,
        },
    },
    "root": {
        "handlers": ["queue_default"],
        "level": LOGGING_SETTINGS.level.upper(),
        "propagate": True,
    },
}
