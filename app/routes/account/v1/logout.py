"""Logout route for the account API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.common.dependencies.client import enforce_logged_in, get_refresh_token
from app.core.jwt.access_token import ACCESS_TOKEN_COOKIE_KWARGS
from app.core.jwt.refresh_token import REFRESH_TOKEN_COOKIE_KWARGS, RefreshToken
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.functions import blacklist_refresh_token
from app.i18n.context_translations import gettext
from app.piccolo.tables.refresh_token import delete_refresh_token

router = APIRouter(
    prefix="/account/v1",
    tags=["account", "logout"],
    dependencies=[Depends(enforce_logged_in())],
)


@router.post("/logout")
async def logout(
    refresh_token: Annotated[RefreshToken | None, Depends(get_refresh_token)],
    redis: Annotated[Redis, Depends(get_redis_client())],
) -> JSONResponse:
    """Logout the user by deleting the refresh token and blacklisting it in Redis.

    Args:
        request (Request): The FastAPI request object.
        refresh_token (RefreshToken | None): The refresh token from the request cookies.
        redis (Redis): The Redis client.

    Raises:
        HTTPException:
            - 400: If the refresh token is not found.
            - 500: If there is an internal server error while deleting or blacklisting the refresh token.

    Returns:
        JSONResponse: A response indicating that the user has been logged out, with cookies deleted.

    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Refresh token not found."),
        )

    # Delete the refresh token from the database
    if not await delete_refresh_token(token=refresh_token):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Internal server error."),
        )

    # Blacklist the refresh token in Redis to prevent its reuse
    if not await blacklist_refresh_token(token=refresh_token, redis=redis):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Internal server error."),
        )

    response = JSONResponse(content={"message": "User logged out successfully."})

    response.delete_cookie(**ACCESS_TOKEN_COOKIE_KWARGS)
    response.delete_cookie(**REFRESH_TOKEN_COOKIE_KWARGS)

    return response
