"""Endpoint dependencies for user login state."""

from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.core.jwt.users import AuthenticatedUser, UnauthenticatedUser
from app.i18n.context_translations import gettext

if TYPE_CHECKING:
    from collections.abc import Callable


def get_user(request: Request) -> AuthenticatedUser | UnauthenticatedUser:
    """Get the user from the request.

    Args:
        request (Request): The FastAPI request object.

    Returns:
        AuthenticatedUser | UnauthenticatedUser: The user object from the request.

    """
    user = request.user

    if not isinstance(user, (AuthenticatedUser, UnauthenticatedUser)):
        raise TypeError(
            f"Expected request.user to be an instance of AuthenticatedUser or UnauthenticatedUser, "
            f"but got {type(user).__name__} instead."
        )

    return user


def get_roles(request: Request) -> frozenset[str]:
    """Get the roles from the request.

    Args:
        request (Request): The FastAPI request object.

    Returns:
        frozenset[str]: The roles of the user from the request.

    """
    roles = request.auth.scopes if hasattr(request.auth, "scopes") else frozenset()

    if not isinstance(roles, frozenset):
        raise TypeError(f"Expected request.auth.scopes to be a frozenset, but got {type(roles).__name__} instead.")

    return roles


def enforce_not_logged_in() -> Callable[[Request], None]:
    """Dependency to enforce that the user is not logged in.

    Returns:
        Callable[[Request], None]: A dependency function that checks the user's login state.

    Raises:
        HTTPException: If the user is logged in.

    """
    def _getter(request: Request) -> None:
        if not isinstance(get_user(request), UnauthenticatedUser):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=gettext("You are already logged in."),
            )

    return _getter


def enforce_logged_in(required_roles: frozenset[str] | None = None) -> Callable[[Request], None]:
    """Dependency to enforce that the user is logged in.

    Args:
        required_roles (frozenset[str] | None): Optional set of roles required to access the resource.

    Returns:
        Callable[[Request], None]: A dependency function that checks the user's login state and roles.

    Raises:
        HTTPException: If the user is not logged in or does not have the required roles.

    """
    def _getter(request: Request) -> None:
        if not isinstance(get_user(request), AuthenticatedUser):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=gettext("You must be logged in to access this resource."),
            )

        if required_roles is not None and not required_roles.issubset(get_roles(request)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=gettext("You do not have the required permissions to access this resource."),
            )

    return _getter
