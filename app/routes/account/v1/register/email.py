"""Initial register route for the account API."""

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
from app.core.smtp.mailer import Mailer
from app.i18n.context_translations import gettext

from .__common import (
    REGISTRATION_COOKIE_KWARGS,
    REGISTRATION_FS_PATH_PARTS,
    REGISTRATION_LOCKOUT_TTL,
    REGISTRATION_URL,
    create_registration,
)
from .__models import InputEmail  # noqa: TC001 -> For Pydantic, it must not be in TYPE_CHECKING

CURRENT_ENDPOINT = Path(__file__).stem
"""Current endpoint name, derived from the file name of this route module."""

REGISTER_NOTIFICATION_SENDER = Mailer(
    subject_template="{{ _('Invitation to Register') }}",
    body_template="registration_invitation.jinja.html",
    private_email=True,
)

router = APIRouter(
    prefix=REGISTRATION_URL + f"/{CURRENT_ENDPOINT}",
    tags=[*REGISTRATION_FS_PATH_PARTS, CURRENT_ENDPOINT],
    dependencies=[Depends(enforce_not_logged_in())],
)


@router.get("/")
async def get_email() -> Response:
    """Render the email submission page for user registration.

    Returns:
        HTMLResponse: The HTML response containing the email submission form.

    """
    content = f"""
    <html>
        <head>
            <title>Register</title>
        </head>
        <body>
            <h1>Register</h1>
            <form action="{REGISTRATION_URL}/{CURRENT_ENDPOINT}" method="post">
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
    """Handle user registration.

    Args:
        request (Request): The FastAPI request object.
        form_data (InputEmail): The user's email address from the form data.
        client_ip_addr (str): The client's IP address for tracking registration attempts.
        password (RawPassword): The user's raw password from the form data.
        redis (Redis): The Redis client for tracking registration attempts.
        background_tasks (BackgroundTasks): FastAPI background tasks for sending emails.
        registration_token (str | None): The registration token from the cookies, if present.

    Returns:
        Response: A JSON response indicating success or failure of the registration process.

    Raises:
        HTTPException: If the registration fails due to exceeding attempt limits or other issues.

    """
    url_token = token_urlsafe(64)
    scheme = request.url.scheme
    hostname = request.url.hostname
    port = request.url.port
    email = form_data.email

    if not await add_access_attempt(
        prefix="registration",
        email=email.get_secret_value(),
        ip=client_ip_addr,
        redis=redis,
        ttl=REGISTRATION_LOCKOUT_TTL,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=gettext("Too many registration attempts. Please try again after %(duration)s minutes.")
            % {"duration": REGISTRATION_LOCKOUT_TTL // 60},
        )

    if not await create_registration(url_token=url_token, email=email.get_secret_value(), redis=redis):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=gettext("Failed to create registration. Please try again later."),
        )

    background_tasks.add_task(
        REGISTER_NOTIFICATION_SENDER.send_email,
        send_to={email.get_secret_value()},
        render_context={"registration_link": f"{scheme}://{hostname}:{port}{REGISTRATION_URL}/alias?token={url_token}"},
    )

    content = """
    <html>
        <head>
            <title>Register</title>
        </head>
        <body>
            <h1>Register</h1>
            <p>Please check your email for further instructions to complete the registration process.</p>
        </body>
    </html>
    """

    response = HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=content,
    )

    response.delete_cookie(**REGISTRATION_COOKIE_KWARGS)
    return response
