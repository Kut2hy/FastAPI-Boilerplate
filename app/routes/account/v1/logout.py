"""Logout route for the account API."""

from logging import getLogger
from typing import Annotated
from uuid import UUID

from asyncpg import InterfaceError, PostgresError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.common.dependencies.client import enforce_logged_in
from app.common.dependencies.cookie_token import get_cookie_token
from app.core.jwt.access_token import ACCESS_TOKEN_COOKIE_KWARGS, AccessToken
from app.core.jwt.refresh_token import REFRESH_TOKEN_COOKIE_KWARGS, RefreshToken
from app.i18n.context_translations import gettext
from app.piccolo.tables.refresh_token import delete_all_refresh_tokens, delete_refresh_token

router = APIRouter(
    prefix="/account/v1",
    tags=["account", "logout"],
    dependencies=[Depends(enforce_logged_in())],
)

LOGGER = getLogger(__name__)


@router.post("/logout")
async def logout(
    request: Request,
    access_token: Annotated[AccessToken | None, Depends(get_cookie_token(token_type=AccessToken))],
    refresh_token: Annotated[RefreshToken | None, Depends(get_cookie_token(token_type=RefreshToken))],
) -> JSONResponse:
    """Logout the user by deleting the refresh token.

    Args:
        request (Request): The FastAPI request object.
        access_token (AccessToken | None): The access token from the request cookies.
        refresh_token (RefreshToken | None): The refresh token from the request cookies.

    Raises:
        HTTPException: (503) If there is a DB issue.

    Returns:
        JSONResponse: A response indicating that the user has been logged out, with cookies deleted.

    """
    try:
        # NOTE: Logging out is based around deleting persistent refresh tokens from the database.
        # This value is stored at 2 places, in the refresh token itself and in the access token as a claim.
        refresh_token_jti = None

        # Get JTI from refresh token itself if available
        if isinstance(refresh_token, RefreshToken):
            refresh_token_jti = refresh_token.token_id

        # Get JTI from access token claim if available as a fallback
        if not refresh_token_jti and isinstance(access_token, AccessToken):
            refresh_token_jti = access_token.extra_claims.get("rt_jti")
            refresh_token_jti = UUID(refresh_token_jti) if refresh_token_jti else None

        # Should not happen, but just in case, if both are missing, all live refresh tokens for the user are deleted.
        # NOTE: As this is "must be logged in" endpoint, request.user.uuid is guaranteed to be present.
        if refresh_token_jti is None:
            LOGGER.warning(
                "Refresh token JTI not found for user %s, performing full logout",
                request.user.uuid,
            )
            await delete_all_refresh_tokens(user_id=request.user.uuid)

        else:
            result = await delete_refresh_token(
                token_id=refresh_token_jti,
                user_id=request.user.uuid,
            )

            if result is None:
                # NOTE: Suspicious scenario, but not impossible. If the refresh token is valid, but not found in the DB.
                # Bad migration, manual DB deletion, or some other unexpected scenario.
                # Just in case, full logout like above is performed.
                LOGGER.warning(
                    "Persistent refresh token not found for user %s, performing full logout", request.user.uuid
                )

                await delete_all_refresh_tokens(user_id=request.user.uuid)

    except (PostgresError, InterfaceError, OSError, TimeoutError) as e:
        LOGGER.warning("Database error while deleting refresh token for user %s", request.user.uuid)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=gettext("Logout service is temporarily unavailable. Please try again later."),
        ) from e

    response = JSONResponse(content={"message": "User logged out successfully."})

    # NOTE: Whole endpoint does not raise a HTTPException -> cookies are destroyed
    # regardless of the outcome of the refresh token deletion.
    response.delete_cookie(**ACCESS_TOKEN_COOKIE_KWARGS)
    response.delete_cookie(**REFRESH_TOKEN_COOKIE_KWARGS)

    return response
