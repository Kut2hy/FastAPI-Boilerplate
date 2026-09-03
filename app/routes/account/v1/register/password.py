"""Register route for the account API."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    Form,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.common.dependencies.client import enforce_not_logged_in
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.session import delete_session, get_session
from app.core.smtp.mailer import Mailer
from app.i18n.context_translations import gettext
from app.piccolo.tables.user_account import account_exists, create_account

from .._redis_state import validate_redis_state
from .._shared_models import (
    AfterAccountInfoState,
    InputPassword,
)
from .__constants import (
    REGISTRATION_COOKIE_KWARGS,
    REGISTRATION_FS_PATH_PARTS,
    REGISTRATION_PREFIX,
    REGISTRATION_URL,
)

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

REGISTER_NOTIFICATION_SENDER = Mailer(
    subject_template="{{ _('Registration Successful') }}",
    body_template="registration_success.jinja.html",
    private_email=True,
)

router = APIRouter(
    prefix=REGISTRATION_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*REGISTRATION_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_password(
    redis: Annotated[Redis, Depends(get_redis_client())],
    registration_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    """Render the password submission page for user registration.

    Args:
        registration_token (str): The registration token from the cookies.
        redis (Redis): The Redis client for retrieving registration information.

    Returns:
        HTMLResponse: An HTML response containing the password submission form.

    Raises:
        HTTPException: If the registration token is invalid or has expired.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis),
        model_class=AfterAccountInfoState,
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
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                <label for="confirm_password">Confirm Password:</label>
                <input type="password" id="confirm_password" name="confirm_password" required>
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
async def post_password(
    form_data: Annotated[InputPassword, Form()],
    redis: Annotated[Redis, Depends(get_redis_client())],
    background_tasks: BackgroundTasks,
    registration_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Handle the password submission for user registration.

    Args:
        registration_token (str): The registration token from the cookies.
        form_data (InputPassword): The user's password and password confirmation from the form data.
        redis (Redis): The Redis client for retrieving registration information.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.

    Returns:
        JSONResponse: A JSON response indicating the success of the password submission.

    Raises:
        HTTPException: If the registration token is invalid or has expired, or if the passwords do not match.

    """
    redis_state_model = validate_redis_state(
        redis_state=await get_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis),
        model_class=AfterAccountInfoState,
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

    if (
        await create_account(
            email=redis_state_model.email,
            alias=redis_state_model.alias,
            password=form_data.password,
            was_email_verified=redis_state_model.valid == "true",
            first_name=redis_state_model.first_name,
            last_name=redis_state_model.last_name,
            middle_name=redis_state_model.middle_name,
            titles_before=redis_state_model.titles_before,
            titles_after=redis_state_model.titles_after,
            phone_number=redis_state_model.phone_number,
            street=redis_state_model.street,
            city=redis_state_model.city,
            postal_code=redis_state_model.postal_code,
            country=redis_state_model.country,
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Failed to create user account. Please try again later."),
        )

    await delete_session(prefix=REGISTRATION_PREFIX, url_token=registration_token, redis=redis)

    background_tasks.add_task(
        REGISTER_NOTIFICATION_SENDER.send_email,
        send_to={redis_state_model.email.get_secret_value()},
        render_context={},
    )

    content = """
    <html>
        <head>
            <title>Register</title>
        </head>
        <body>
            <h1>Registration Successful</h1>
            <p>Your account has been successfully created.</p>
        </body>
    </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.delete_cookie(**REGISTRATION_COOKIE_KWARGS)
    return response
