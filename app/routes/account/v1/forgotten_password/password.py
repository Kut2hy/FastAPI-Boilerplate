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
    Request,
    status,
)
from fastapi.responses import RedirectResponse, Response

from app.common.dependencies.client import enforce_not_logged_in
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.session import delete_session, get_session, update_session
from app.core.smtp.mailer import Mailer
from app.core.templating.v1.response import HTMXTemplatedResponse, PartialResponseFragment
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
    FORGOTTEN_PASSW_FS_PATH,
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
async def get_password(
    request: Request,
    token: Annotated[str, Query()],
    redis: Annotated[Redis, Depends(get_redis_client())],
) -> Response:
    """Handle the password reset for forgotten password.

    Args:
        request (Request): The FastAPI request object.
        token (str): The forgotten password token from the query parameters.
        redis (Redis): The Redis client for retrieving forgotten password information.

    Returns:
        HTMLResponse: An HTML response containing the password reset form.

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

    response = HTMXTemplatedResponse(
        request=request,
        status_code=status.HTTP_200_OK,
        title=gettext("Forgotten Password - Reset"),
        fragments=(
            PartialResponseFragment(
                name="main",
                path=f"routes/{FORGOTTEN_PASSW_FS_PATH}/{CURRENT_ENDPOINT}.get.jinja.html",
            ),
        ),
    )

    response.set_cookie(**FORGOTTEN_PASSW_COOKIE_KWARGS, value=new_token, expires=FORGOTTEN_PASSW_KEY_TTL)

    return response


@router.post("/")
async def post_password(
    request: Request,
    form_data: Annotated[InputPassword, Form()],
    redis: Annotated[Redis, Depends(get_redis_client())],
    background_tasks: BackgroundTasks,
    forgotten_passw_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Handle the password submission for forgotten password.

    Args:
        request (Request): The incoming HTTP request.
        forgotten_passw_token (str): The forgotten password token from the cookies.
        form_data (InputPassword): The user's password and password confirmation from the form data.
        redis (Redis): The Redis client for retrieving forgotten password information.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.

    Returns:
        Response: An HTTP response indicating the success of the password submission.

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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=gettext("Failed to change password."),
        )

    await delete_session(prefix=FORGOTTEN_PASSW_PREFIX, url_token=forgotten_passw_token, redis=redis)

    background_tasks.add_task(
        NOTIFICATION_SENDER.send_email,
        send_to={redis_state_model.email.get_secret_value()},
        render_context={},
    )

    response = HTMXTemplatedResponse(
        request=request,
        status_code=status.HTTP_200_OK,
        title=gettext("Forgotten Password - Password Changed"),
        fragments=(
            PartialResponseFragment(
                name="main",
                path=f"routes/{FORGOTTEN_PASSW_FS_PATH}/{CURRENT_ENDPOINT}.post.jinja.html",
            ),
        ),
    )

    response.delete_cookie(**FORGOTTEN_PASSW_COOKIE_KWARGS)
    return response
