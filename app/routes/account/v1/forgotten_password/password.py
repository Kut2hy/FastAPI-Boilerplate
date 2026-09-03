"""Forgotten password route for the account API."""

from pathlib import Path
from secrets import token_urlsafe
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from app.core.smtp.mailer import Mailer
from app.i18n.context_translations import gettext
from app.piccolo.tables.user_account import account_exists, change_password

from .._redis_state import validate_redis_state
from .._shared_models import (
    AfterClickThroughState,
    AfterCreationState,
    InputPassword,
)
from .__constants import (
    FORGOTTEN_PASSW_COOKIE_KWARGS,
    FORGOTTEN_PASSW_FS_PATH_PARTS,
    FORGOTTEN_PASSW_KEY_TTL,
    FORGOTTEN_PASSW_PREFIX,
    FORGOTTEN_PASSW_URL,
)

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

NOTIFICATION_SENDER = Mailer(
    subject_template="{{ _('Password Reset Successful') }}",
    body_template="forgotten_passw_success.jinja.html",
    private_email=True,
)

router = APIRouter(
    prefix=FORGOTTEN_PASSW_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*FORGOTTEN_PASSW_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_alias(
    token: Annotated[str, Query()],
    redis: Annotated[Redis, Depends(get_redis_client())],
) -> Response:
    """Handle the password retrieval for forgotten password.

    Args:
        token (str): The forgotten password token from the query parameters.
        redis (Redis): The Redis client for retrieving forgotten password information.

    Returns:
        HTMLResponse: An HTML response containing the email associated with the registration token.

    Raises:
        HTTPException: If the forgotten password token is invalid or has expired.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=token, redis=redis),
        model_class=AfterCreationState,
    )

    if redis_state_model is None:
        await delete_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired forgotten password token."),
        )

    # Validate that account was not deleted in the meantime.
    email_exists, _ = await account_exists(email=redis_state_model.email.get_secret_value(), alias=None)
    if not email_exists:
        await delete_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=token, redis=redis)
        return RedirectResponse(
            url="/",
            status_code=status.HTTP_303_SEE_OTHER,
            # TODO: Add toast event to inform the user that the account has been deleted.
        )

    new_token = token_urlsafe(64)
    if not await update_session(
        prefix=FORGOTTEN_PASSW_PREFIX, url_token=token, new_url_token=new_token, mapping={"valid": "true"}, redis=redis
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Internal server error."),
        )

    content = f"""
        <html>
            <head>
                <title>Reset Password</title>
            </head>
            <body>
                <h1>Reset Password</h1>
                <form action="{FORGOTTEN_PASSW_URL}/{CURRENT_ENDPOINT}" method="post">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                    <label for="confirm_password">Confirm Password:</label>
                    <input type="password" id="confirm_password" name="confirm_password" required>
                    <button type="submit">Submit</button>
                </form>
            </body>
        </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.set_cookie(**FORGOTTEN_PASSW_COOKIE_KWARGS, value=new_token, expires=FORGOTTEN_PASSW_KEY_TTL)

    return response


@router.post("/")
async def post_password(
    form_data: Annotated[InputPassword, Form()],
    redis: Annotated[Redis, Depends(get_redis_client())],
    background_tasks: BackgroundTasks,
    forgotten_passw_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Handle the password submission for forgotten password.

    Args:
        forgotten_passw_token (str): The forgotten password token from the cookies.
        form_data (InputPassword): The user's password and password confirmation from the form data.
        redis (Redis): The Redis client for retrieving forgotten password information.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.

    Returns:
        JSONResponse: A JSON response indicating the success of the password submission.

    Raises:
        HTTPException: If the forgotten password token is invalid or has expired, or if the passwords do not match.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=forgotten_passw_token, redis=redis),
        model_class=AfterClickThroughState,
    )

    if redis_state_model is None:
        await delete_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=forgotten_passw_token, redis=redis)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Invalid or expired forgotten password token."),
        )

    if not await change_password(email=redis_state_model.email, new_password=form_data.password):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Failed to change password."),
        )

    await delete_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=forgotten_passw_token, redis=redis)

    background_tasks.add_task(
        NOTIFICATION_SENDER.send_email,
        send_to={redis_state_model.email.get_secret_value()},
        render_context={},
    )

    content = """
    <html>
        <head>
            <title>Reset Password</title>
        </head>
        <body>
            <h1>Password Reset Successful</h1>
            <p>Your password has been successfully reset.</p>
        </body>
    </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.delete_cookie(**FORGOTTEN_PASSW_COOKIE_KWARGS)
    return response
