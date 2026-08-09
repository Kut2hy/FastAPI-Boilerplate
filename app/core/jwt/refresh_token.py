"""Module for creating and validating refresh tokens."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.app_config import APP_SETTINGS
from app.core.jwt._base_token import BaseToken


class RefreshTokenSettings(BaseSettings):
    """Pydantic environment settings for refresh tokens."""

    model_config = SettingsConfigDict(
            frozen=True,
            env_file=".env",
            env_prefix="REFRESH_TOKEN_",
            env_file_encoding="utf-8",
            dotenv_filtering="match_prefix",
        )

    secret_key: SecretStr = Field(min_length=32, max_length=128)
    """The secret key used to sign the refresh token. It should be a long, random string to ensure security."""

    algorithm: str = Field(default="HS512")
    """The algorithm used to sign the refresh token. Default is HS512."""

    time_to_live: int = Field(default=60, ge=1)
    """The time to live for the refresh token in seconds. Default is 60 seconds (1 minute)."""


REFRESH_TOKEN_SETTINGS: RefreshTokenSettings = RefreshTokenSettings.model_validate({})
"""Instance of the RefreshTokenSettings class containing the validated environment settings."""

_APP_VERSION = APP_SETTINGS.version
"""
A version string for the application. This can be included in the token claims, and when the application is updated,
the version can be changed to invalidate all existing tokens.
"""

_HOSTNAME = str(APP_SETTINGS.host)
"""The hostname of the application."""

_ISSUER = "|".join(
    (
        # "RefreshToken",
        _HOSTNAME,
        _APP_VERSION,
    )
)
"""The issuer claim value for the refresh token."""


class RefreshToken(BaseToken):
    """Class for refresh tokens.

    When class instances are loaded from string, code to validate token and claims will be executed.
    If validation fails, an exception will be raised.

    Implemented claims:
    - 'jti' (JWT ID): A UUID that uniquely identifies the token.
    - 'iss' (Issuer): Identifies the principal that issued the JWT.
    - 'aud' (Audience): Identifies the recipients that the JWT is intended for.
    - 'sub' (Subject): A UUID that points to the user the token is issued for.
    - 'iat' (Issued At): The time at which the JWT was issued [seconds since epoch].
    - 'nbf' (Not Before): The time before which the JWT must not be accepted for processing [seconds since epoch].
    - 'exp' (Expiration Time): The time after which the JWT expires [seconds since epoch].
    - 'at_hash' (Access Token Hash): A hash of the access token that can be used to validate that
        the access token was issued with the refresh token.
    """

    cookies_name: str = "refresh_token"
    """The name of the cookie where the refresh token is stored."""

    algorithm: str = "HS512"
    """The algorithm used to sign the refresh token."""

    allowed_extra_claims: frozenset[str] = frozenset(
        {
            # Access Token hash. This can be used to validate that the access token was issued with the refresh token.
            "at_hash",
        }
    )
    """A set of allowed extra claims that can be included in the refresh token."""

    _issuer: str = _ISSUER
    """The issuer claim value for the refresh token."""

    time_to_live: int = 2592000  # 30 days in seconds
    """The time to live for the refresh token in seconds."""

    _secret_key: str = REFRESH_TOKEN_SETTINGS.secret_key.get_secret_value()
    """The secret key used to sign the refresh token."""


REFRESH_TOKEN_COOKIE_KWARGS = {
    "key": RefreshToken.cookies_name,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": "/",
}
"""Common keyword arguments for setting and deleting the refresh token cookie to ensure consistency and security."""
