"""Initial forgotten password route for the account API."""

from pathlib import Path
from secrets import token_urlsafe
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import HTMLResponse, Response
from slowapi.util import get_remote_address

from app.common.dependencies.client import enforce_not_logged_in
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.limiter import add_access_attempt
from app.core.redis.session import create_session
from app.core.smtp.mailer import Mailer
from app.i18n.context_translations import gettext

from .._shared_models import InputEmail  # noqa: TC001 -> For Pydantic, it must not be in TYPE_CHECKING
from .__constants import (
    FORGOTTEN_PASSW_COOKIE_KWARGS,
    FORGOTTEN_PASSW_FS_PATH_PARTS,
    FORGOTTEN_PASSW_LOCKOUT_TTL,
    FORGOTTEN_PASSW_PREFIX,
    FORGOTTEN_PASSW_URL,
)

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

FORGOTTEN_PASSW_NOTIFICATION_SENDER = Mailer(
    subject_template="{{ _('Forgotten Password Request') }}",
    body_template="forgotten_passw_invitation.jinja.html",
    private_email=True,
)

router = APIRouter(
    prefix=FORGOTTEN_PASSW_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*FORGOTTEN_PASSW_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_email() -> Response:
    """Render the email submission page for users who have forgotten their password.

    Returns:
        HTMLResponse: The HTML response containing the email submission form for forgotten password.

    """
    content = f"""
    <html>
        <head>
            <title>Forgotten Password</title>
        </head>
        <body>
            <h1>Forgotten Password</h1>
            <form action="{FORGOTTEN_PASSW_URL}/{CURRENT_ENDPOINT}" method="post">
                <label for="email">Email:</label>
                <input type="email" id="email" name="email" required>
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
async def post_email(
    request: Request,
    form_data: Annotated[InputEmail, Form()],
    client_ip_addr: Annotated[str, Depends(get_remote_address)],
    redis: Annotated[Redis, Depends(get_redis_client())],
    background_tasks: BackgroundTasks,
) -> Response:
    """Handle forgotten password request.

    Args:
        request (Request): The FastAPI request object.
        form_data (InputEmail): The user's email address from the form data.
        client_ip_addr (str): The client's IP address for tracking forgotten password attempts.
        redis (Redis): The Redis client for tracking forgotten password attempts.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        FORGOTTEN_PASSW_token (str | None): The forgotten password token from the cookies, if present.

    Returns:
        Response: A JSON response indicating success or failure of the forgotten password process.

    Raises:
        HTTPException: If the forgotten password request fails due to exceeding attempt limits or other issues.

    """
    url_token = token_urlsafe(64)
    scheme = request.url.scheme
    hostname = request.url.hostname
    port = request.url.port
    email = form_data.email

    if not await add_access_attempt(
        prefix=FORGOTTEN_PASSW_PREFIX,
        email=email.get_secret_value(),
        ip=client_ip_addr,
        redis=redis,
        ttl=FORGOTTEN_PASSW_LOCKOUT_TTL,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=gettext("Too many forgotten password attempts. Please try again after %(duration)s minutes.")
            % {"duration": FORGOTTEN_PASSW_LOCKOUT_TTL // 60},
        )

    if not await create_session(
        prefix=FORGOTTEN_PASSW_PREFIX, url_token=url_token, email=email.get_secret_value(), redis=redis
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Failed to create forgotten password entry. Please try again later."),
        )

    background_tasks.add_task(
        FORGOTTEN_PASSW_NOTIFICATION_SENDER.send_email,
        send_to={email.get_secret_value()},
        render_context={
            "forgotten_passw_link": f"{scheme}://{hostname}:{port}{FORGOTTEN_PASSW_URL}/password?token={url_token}"
        },
    )

    content = """
    <html>
        <head>
            <title>Forgotten Password</title>
        </head>
        <body>
            <h1>Forgotten Password</h1>
            <p>Please check your email for further instructions to reset your password.</p>
        </body>
    </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.delete_cookie(**FORGOTTEN_PASSW_COOKIE_KWARGS)
    return response
