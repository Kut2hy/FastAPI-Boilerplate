"""Port of Starlette's set/delete cookie functions to be used in ASGI middleware."""

from datetime import datetime
from email.utils import format_datetime
from http.cookies import BaseCookie, SimpleCookie
from typing import Literal


def set_cookie(
    key: str,
    value: str = "",
    max_age: int | None = None,
    expires: datetime | str | int | None = None,
    path: str | None = "/",
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] | None = "lax",
    partitioned: bool = False,
) -> str:
    """Set a cookie with the given parameters.

    Args:
        key (str):
            The name of the cookie.
        value (str):
            The value of the cookie. Default is an empty string.
        max_age (int | None):
            The maximum age of the cookie in seconds. Default is None.
        expires (datetime | str | int | None):
            The expiration date of the cookie. Can be a datetime object, a string in the correct format, or an integer
            representing seconds since the epoch. Default is None.
        path (str | None):
            The path for which the cookie is valid. Default is "/".
        domain (str | None):
            The domain for which the cookie is valid. Default is None.
        secure (bool):
            Whether the cookie should be marked as secure. Default is False.
        httponly (bool):
            Whether the cookie should be marked as HTTP-only. Default is False.
        samesite (Literal["lax", "strict", "none"] | None):
            The SameSite attribute of the cookie. Default is "lax".
        partitioned (bool):
            Whether the cookie should be marked as partitioned. Default is False.

    Returns:
        str: The formatted Set-Cookie header string.

    """

    cookie: BaseCookie[str] = SimpleCookie()

    # Set the cookie value and attributes
    cookie[key] = value

    if max_age is not None:
        cookie[key]["max-age"] = max_age

    if expires is not None:
        cookie[key]["expires"] = format_datetime(expires, usegmt=True) if isinstance(expires, datetime) else expires

    if path is not None:
        cookie[key]["path"] = path

    if domain is not None:
        cookie[key]["domain"] = domain

    if secure:
        cookie[key]["secure"] = True

    if httponly:
        cookie[key]["httponly"] = True

    if samesite is not None:
        cookie[key]["samesite"] = samesite

    # NOTE: Starlette has a Python 3.14+ validation, but this app is meant to run on 3.14 or higher,
    #   so no need to validate the partitioned attribute here.
    if partitioned:
        cookie[key]["partitioned"] = True

    return cookie.output(header="").strip()


def delete_cookie(
    key: str,
    path: str = "/",
    domain: str | None = None,
    secure: bool = False,
    httponly: bool = False,
    samesite: Literal["lax", "strict", "none"] | None = "lax",
) -> str:
    """Delete a cookie by setting its value to an empty string and its expiration date to a past date.

    Args:
        key (str):
            The name of the cookie to delete.
        path (str):
            The path for which the cookie is valid. Default is "/".
        domain (str | None):
            The domain for which the cookie is valid. Default is None.
        secure (bool):
            Whether the cookie should be marked as secure. Default is False.
        httponly (bool):
            Whether the cookie should be marked as HTTP-only. Default is False.
        samesite (Literal["lax", "strict", "none"] | None):
            The SameSite attribute of the cookie. Default is "lax".

    Returns:
        str: The formatted Set-Cookie header string to delete the cookie.

    """
    return set_cookie(
        key,
        value="",
        max_age=0,
        expires=0,
        path=path,
        domain=domain,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
    )
