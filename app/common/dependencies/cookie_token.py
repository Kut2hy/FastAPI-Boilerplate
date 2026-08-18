"""Module containing dependencies for the authentication endpoints."""

from typing import TYPE_CHECKING, overload

from fastapi import (
    Request,  # noqa: TC002 -> Must be a runtime import so FastAPI can resolve it for dependency injection.
)
from jwt.exceptions import InvalidTokenError

from app.core.jwt.access_token import AccessToken
from app.core.jwt.refresh_token import RefreshToken

if TYPE_CHECKING:
    from collections.abc import Callable


CookieTokens = AccessToken | RefreshToken
"""Composite type representing JWT tokens stored in cookies."""


@overload
def get_cookie_token(
    token_type: type[AccessToken],
) -> Callable[[Request], AccessToken]: ...

@overload
def get_cookie_token(
    token_type: type[RefreshToken],
) -> Callable[[Request], RefreshToken | None]: ...


def get_cookie_token(
    token_type: type[CookieTokens],
) -> Callable[[Request], CookieTokens | None]:
    """Dependency to get a cookie token from the request context.

    Args:
        token_type (type[CookieTokens]): The type of token to retrieve from the cookies.

    Returns:
        (Callable[[Request], CookieTokens | None]): A callable that takes a Request and
            returns the cookie token of the specified type or None if the token is missing or invalid.

    """

    def _getter(request: Request) -> CookieTokens | None:
        try:
            token_cookie = request.cookies.get(token_type.cookies_name)

            if not token_cookie:
                return None

            token = token_type.from_string(token_cookie, token_type.acceptable_leeway)

        except InvalidTokenError:
            return None

        else:
            return token

    return _getter
