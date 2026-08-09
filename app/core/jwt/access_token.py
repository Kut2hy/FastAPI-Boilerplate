"""Module for creating and validating access tokens."""


from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.app_config import APP_SETTINGS
from app.core.jwt._base_token import BaseToken


class AccessTokenSettings(BaseSettings):
    """Pydantic environment settings for access tokens."""

    model_config = SettingsConfigDict(
            frozen=True,
            env_file=".env",
            env_prefix="ACCESS_TOKEN_",
            env_file_encoding="utf-8",
            dotenv_filtering="match_prefix",
        )

    secret_key: SecretStr = Field(min_length=32, max_length=128)
    """The secret key used to sign the access token. It should be a long, random string to ensure security."""

    algorithm: str = Field(default="HS512")
    """The algorithm used to sign the access token. Default is HS512."""

    time_to_live: int = Field(default=60, ge=1)
    """The time to live for the access token in seconds. Default is 60 seconds (1 minute)."""


ACCESS_TOKEN_SETTINGS: AccessTokenSettings = AccessTokenSettings.model_validate({})
"""Instance of the AccessTokenSettings class containing the validated environment settings."""

_APP_VERSION = APP_SETTINGS.version
"""
A version string for the application. This can be included in the token claims, and when the application is updated,
the version can be changed to invalidate all existing tokens.
"""

_HOSTNAME = str(APP_SETTINGS.host)
"""The hostname of the application."""

_ISSUER = "|".join(
    (
        # "AccessToken",
        _HOSTNAME,
        _APP_VERSION,
    )
)
"""The issuer claim value for the access token."""


class AccessToken(BaseToken):
    """Class for access tokens.

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
    """

    cookies_name: str = "access_token"
    """The name of the cookie where the access token is stored."""

    algorithm: str = ACCESS_TOKEN_SETTINGS.algorithm
    """The algorithm used to sign the access token."""

    allowed_extra_claims: frozenset[str] = frozenset(("roles", "rt_hash", "alias"))
    """A set of allowed extra claims that can be included in the access token."""

    _issuer: str = _ISSUER
    """The issuer claim value for the access token."""

    time_to_live: int = ACCESS_TOKEN_SETTINGS.time_to_live
    """The time to live for the access token in seconds."""

    _secret_key: str = ACCESS_TOKEN_SETTINGS.secret_key.get_secret_value()
    """The secret key used to sign the access token."""


ACCESS_TOKEN_COOKIE_KWARGS = {
    "key": AccessToken.cookies_name,
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": "/",
}
"""Common keyword arguments for setting and deleting the access token cookie to ensure consistency and security."""
