"""Register route for the account API."""

from pathlib import Path
from secrets import token_urlsafe
from typing import Annotated

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.common.dependencies.client import enforce_not_logged_in
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.session import delete_session, get_session, update_session
from app.i18n.context_translations import gettext
from app.piccolo.tables.user_account import account_exists

from .._redis_state import validate_redis_state
from .._shared_models import (
    AfterClickThroughState,
    AfterCreationState,
)
from .__constants import (
    REGISTRATION_COOKIE_KWARGS,
    REGISTRATION_FS_PATH_PARTS,
    REGISTRATION_KEY_TTL,
    REGISTRATION_PREFIX,
    REGISTRATION_URL,
)

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

NEXT_ENDPOINT = "info"
"""Next endpoint name in the registration flow, used for redirection after alias submission."""

router = APIRouter(
    prefix=REGISTRATION_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*REGISTRATION_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_alias(
    token: Annotated[str, Query()],
    redis: Annotated[Redis, Depends(get_redis_client())],
) -> Response:
    """Handle the alias retrieval for user registration.

    Args:
        token (str): The registration token from the query parameters.
        redis (Redis): The Redis client for retrieving registration information.

    Returns:
        HTMLResponse: An HTML response containing the email associated with the registration token.

    Raises:
        HTTPException: If the registration token is invalid or has expired.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=token, redis=redis),
        model_class=AfterCreationState,
    )

    if redis_state_model is None:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired registration."),
        )

    # Validate that account with the same email or alias was not already created in the meantime.
    email_exists, _ = await account_exists(email=redis_state_model.email.get_secret_value(), alias=None)
    if email_exists:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=token, redis=redis)
        return RedirectResponse(
            url="/",
            status_code=status.HTTP_303_SEE_OTHER,
            # TODO: Add toast event to inform the user that the email is already in use.
        )

    # If process gets here, it is a valid registration coming from actual email.
    new_token = token_urlsafe(64)

    # NOTE: Redis key renaming feature of "update_registration" is important here.
    #   It ensures that token send to user via email is usable only once.
    #   If user clicks the link again, it will be invalid and they will have to start over.
    if not await update_session(
        prefix=REGISTRATION_PREFIX, url_token=token, new_url_token=new_token, mapping={"valid": "true"}, redis=redis
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Internal server error."),
        )

    content = f"""
    <html>
        <head>
            <title>Register</title>
        </head>
        <body>
            <h1>Register</h1>
            <form action="{REGISTRATION_URL}/{CURRENT_ENDPOINT}" method="post">
                <label for="alias">Alias:</label>
                <input type="text" id="alias" name="alias" required>
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.set_cookie(**REGISTRATION_COOKIE_KWARGS, value=new_token, expires=REGISTRATION_KEY_TTL)

    return response


@router.post("/")
async def post_alias(
    alias: Annotated[str, Form()],
    redis: Annotated[Redis, Depends(get_redis_client())],
    registration_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Handle the alias submission for user registration.

    Args:
        registration_token (str| None): The registration token from the cookies.
        alias (str): The alias to associate with the user account.
        redis (Redis): The Redis client for retrieving registration information.

    Returns:
        JSONResponse: A JSON response indicating the success of the alias submission.

    Raises:
        HTTPException: If the registration token is invalid or has expired.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis),
        model_class=AfterClickThroughState,
    )

    if redis_state_model is None:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired registration."),
        )

    # Validate that account with the same email or alias was not already created in the meantime.
    email_exists, alias_exists = await account_exists(email=redis_state_model.email.get_secret_value(), alias=alias)

    if email_exists:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis)
        response = RedirectResponse(
            url="/",
            status_code=status.HTTP_303_SEE_OTHER,
            # TODO: Add toast event to inform the user that the email is already in use.
        )

        response.delete_cookie(**REGISTRATION_COOKIE_KWARGS)
        return response

    if alias_exists:
        return RedirectResponse(
            url=f"{REGISTRATION_URL}/alias?token={registration_token}",
            status_code=status.HTTP_303_SEE_OTHER,
            # TODO: Add toast event to inform the user that the alias is already in use.
        )

    new_token = token_urlsafe(64)
    if not await update_session(
        prefix=REGISTRATION_PREFIX,
        url_token=registration_token,
        new_url_token=new_token,
        mapping={"alias": alias},
        redis=redis,
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Internal server error."),
        )

    response = RedirectResponse(
        url=f"{REGISTRATION_URL}/{NEXT_ENDPOINT}",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    response.set_cookie(**REGISTRATION_COOKIE_KWARGS, value=new_token, expires=REGISTRATION_KEY_TTL)
    return response
