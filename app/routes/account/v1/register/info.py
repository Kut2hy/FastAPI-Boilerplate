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
    AfterAliasState,
    InputAccountInfo,
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

NEXT_ENDPOINT = "password"
"""Next endpoint name in the registration flow, used for redirection after alias submission."""

router = APIRouter(
    prefix=REGISTRATION_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*REGISTRATION_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_info(
    redis: Annotated[Redis, Depends(get_redis_client())],
    registration_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    """Retrieve the registration information after alias submission.

    Args:
        registration_token (str): The registration token from the cookies.
        redis (Redis): The Redis client for retrieving registration information.

    Returns:
        JSONResponse: A JSON response containing the registration information.

    Raises:
        HTTPException: If the registration token is invalid or has expired.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis),
        model_class=AfterAliasState,
    )

    if redis_state_model is None:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired registration."),
        )

    content = f"""
    <html>
        <head>
            <title>Register</title>
        </head>
        <body>
            <h1>Register</h1>
            <form action="{REGISTRATION_URL}/{CURRENT_ENDPOINT}" method="post">
                <label for="first_name">First Name:</label>
                <input type="text" id="first_name" name="first_name" required>
                <label for="middle_name">Middle Name:</label>
                <input type="text" id="middle_name" name="middle_name" required>
                <label for="last_name">Last Name:</label>
                <input type="text" id="last_name" name="last_name" required>
                <label for="titles_before">Titles Before:</label>
                <input type="text" id="titles_before" name="titles_before">
                <label for="titles_after">Titles After:</label>
                <input type="text" id="titles_after" name="titles_after">
                <label for="phone_number">Phone Number:</label>
                <input type="text" id="phone_number" name="phone_number">
                <label for="street">Street:</label>
                <input type="text" id="street" name="street">
                <label for="city">City:</label>
                <input type="text" id="city" name="city">
                <label for="postal_code">Postal Code:</label>
                <input type="text" id="postal_code" name="postal_code">
                <label for="country">Country:</label>
                <input type="text" id="country" name="country">
                <button type="submit">Submit</button>
            </form>
        </body>
    </html>
    """

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )


@router.post("/")
async def post_info(
    form_data: Annotated[InputAccountInfo, Form()],
    redis: Annotated[Redis, Depends(get_redis_client())],
    registration_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis),
        model_class=AfterAliasState,
    )

    if redis_state_model is None:
        await delete_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired registration."),
        )

    email_exists, alias_exists = await account_exists(
        email=redis_state_model.email.get_secret_value(),
        alias=redis_state_model.alias,
    )

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
        mapping=form_data.model_dump_table(exclude_none=True, exclude_unset=True),
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
