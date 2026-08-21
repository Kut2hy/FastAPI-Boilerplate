"""Email/SMTP configuration."""

from typing import Annotated

from pydantic import EmailStr, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SMTPSettings(BaseSettings):
    """SMTP settings."""

    model_config = SettingsConfigDict(
        frozen=True,
        env_file=".env",
        env_prefix="SMTP_",
        env_file_encoding="utf-8",
        dotenv_filtering="match_prefix",
    )

    host: Annotated[str, Field(default="127.0.0.1")]
    """SMTP host for sending emails from the app."""

    port: Annotated[int, Field(default=587, ge=1, le=65535)]
    """SMTP port for sending emails from the app."""

    user: Annotated[str | None, Field(default=None)]
    """SMTP username for sending emails from the app."""

    password: Annotated[SecretStr | None, Field(default=None)]
    """SMTP password for sending emails from the app."""

    from_name: Annotated[str, Field(...)]
    """From name for emails sent from the app."""

    from_email: Annotated[EmailStr, Field(...)]
    """From email for emails sent from the app."""

    cc_email: Annotated[EmailStr, Field(...)]
    """CC email to app admin for emails sent from the app."""

    starttls: Annotated[bool, Field(default=True)]
    """Whether to use STARTTLS for the SMTP connection."""

    @model_validator(mode="before")
    @classmethod
    def validate_auth(cls, values: dict) -> dict:
        """Validate that if user is provided, password must also be provided."""
        user = values.get("user")
        password = values.get("password")

        if user and not password:
            raise ValueError("SMTP password must be provided if SMTP user is set.")

        if password and not user:
            raise ValueError("SMTP user must be provided if SMTP password is set.")

        return values


SMTP_SETTINGS: SMTPSettings = SMTPSettings.model_validate({})
"""Instance of the SMTPSettings class containing the validated environment settings."""
