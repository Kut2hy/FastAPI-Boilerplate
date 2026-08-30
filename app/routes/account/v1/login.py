"""Login route for the account API."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address

from app.common.dependencies.client import enforce_not_logged_in
from app.common.pydantic_classes.types.email import (
    Email,  # noqa: TC001 -> For Pydantic, it must not be in TYPE_CHECKING
)
from app.common.pydantic_classes.types.password import (
    RawPassword,  # noqa: TC001 -> For Pydantic, it must not be in TYPE_CHECKING
)
from app.core.jwt.access_token import ACCESS_TOKEN_COOKIE_KWARGS, AccessToken
from app.core.jwt.refresh_token import REFRESH_TOKEN_COOKIE_KWARGS, RefreshToken
from app.core.password import hash_password, verify_password
from app.core.redis.dependencies import Redis, get_redis_client
from app.core.redis.limiter import add_access_attempt, reset_access_attempt
from app.core.smtp.mailer import Mailer
from app.i18n.context_translations import gettext
from app.piccolo.tables.login_attempt import add_login_attempt as add_login_audit_trace
from app.piccolo.tables.refresh_token import add_refresh_token
from app.piccolo.tables.user_account import get_user

BASE_FS_PATH = "/account/v1"

router = APIRouter(
    prefix=BASE_FS_PATH.replace("-", "_"),
    tags=["account", "login"],
    dependencies=[Depends(enforce_not_logged_in())],
)

ATTEMPT_LIMIT = 3
"""Maximum number of login attempts allowed before lockout."""

ATTEMPT_LOCKOUT_DURATION = 3600
"""Lockout duration in seconds after exceeding the maximum number of login attempts."""

ATTEMPT_PREFIX = "login"
"""Prefix for Redis keys related to login attempts."""

DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing")
"""Dummy password hash used to mitigate timing attacks when the user does not exist."""

LOGIN_NOTIFICATION_SENDER = Mailer(
    subject_template="{{ _('Successful Login Notification') }}",
    body_template="login_notification.jinja.html",
    private_email=True,
)


# NOTE: SlowAPI's rate limiting is not used here because it does not provide the flexibility needed to track
# login attempts by both email and IP address, and to enforce lockout durations based on those attempts.
@router.post("/login")
async def login(
    email: Annotated[Email, Form()],
    password: Annotated[RawPassword, Form()],
    client_ip_addr: Annotated[str, Depends(get_remote_address)],
    redis: Annotated[Redis, Depends(get_redis_client())],
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Login endpoint for user authentication.

    Args:
        email (Email): The user's email address.
        password (RawPassword): The user's raw password.
        client_ip_addr (str): The client's IP address, obtained from the request.
        redis (Redis): The Redis client for tracking login attempts.
        background_tasks (BackgroundTasks): FastAPI background tasks for asynchronous operations.

    Returns:
        JSONResponse: A response containing the access and refresh tokens if login is successful.

    Raises:
        HTTPException:
          - 401 Unauthorized: If the email or password is invalid.
          - 403 Forbidden: If the account is locked, email is not verified, or account is pending review.
          - 429 Too Many Requests: If the maximum number of login attempts has been exceeded.
          - 500 Internal Server Error: If there is an issue adding the refresh token

    """
    # NOTE: Limit exception is not logged as it beats the purpose of having Redis track login attempts,
    #   which is to prevent brute-force attacks.
    if not await add_access_attempt(
        prefix=ATTEMPT_PREFIX,
        email=email.get_secret_value(),
        ip=client_ip_addr,
        redis=redis,
        ttl=ATTEMPT_LOCKOUT_DURATION,
        limit=ATTEMPT_LIMIT,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=gettext("Too many login attempts. Please try again after %(duration)s minutes.")
            % {"duration": ATTEMPT_LOCKOUT_DURATION // 60},
        )

    try:
        user_account = await get_user(email.get_secret_value())

        # IMPORTANT: Verify that it is a registered user, if not use a dummy password hash to mitigate timing attacks.
        if not user_account:
            _ = verify_password(password.get_secret_value(), DUMMY_PASSWORD_HASH)

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=gettext("Invalid email or password."),
            )

        if not verify_password(password.get_secret_value(), user_account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=gettext("Invalid email or password."),
            )

        # Validate the user's account states that may prevent login, such as locked accounts,
        #   unverified emails, or pending reviews.
        if user_account.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=gettext("Your account is locked. Please contact support."),
            )

        if not user_account.was_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=gettext("Your email address has not been verified. Please check your inbox."),
            )

        if not user_account.was_reviewed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=gettext("Your account is pending review. Please wait for approval."),
            )

        user_id = user_account.id
        alias = user_account.user_alias
        roles = ",".join(user_account.granted_roles)

        # Generate access and refresh tokens for the authenticated user.
        refresh_token = RefreshToken.generate_token(subject=user_id)
        access_token = AccessToken.generate_token(
            subject=user_id, alias=alias, roles=roles, rt_jti=str(refresh_token.token_id)
        )

        # Store the refresh token in the database to allow for future validation and revocation.
        if not await add_refresh_token(token=refresh_token):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=gettext("Internal server error."),
            )

    except HTTPException as e:
        # Log the failed login attempt for auditing purposes, including the email, IP address, and status code.
        await add_login_audit_trace(
            user_email=email.get_secret_value(),
            user_ip_address=client_ip_addr,
            status_code=e.status_code,
        )

        raise

    else:
        # Log the successful login attempt for auditing purposes, including the email, IP address, and status code.
        background_tasks.add_task(
            add_login_audit_trace,
            user_email=email.get_secret_value(),
            user_ip_address=client_ip_addr,
            status_code=status.HTTP_200_OK,
        )

    # Clear Redis limits
    await reset_access_attempt(
        prefix=ATTEMPT_PREFIX,
        email=email.get_secret_value(),
        ip=client_ip_addr,
        redis=redis,
    )

    response = JSONResponse(content={"message": "User logged in successfully."})

    response.set_cookie(
        **ACCESS_TOKEN_COOKIE_KWARGS,
        value=str(access_token),
        expires=datetime.fromtimestamp(access_token.expiration, tz=timezone.utc),
    )
    response.set_cookie(
        **REFRESH_TOKEN_COOKIE_KWARGS,
        value=str(refresh_token),
        expires=datetime.fromtimestamp(refresh_token.expiration, tz=timezone.utc),
    )

    background_tasks.add_task(
        LOGIN_NOTIFICATION_SENDER.send_email,
        send_to={
            user_account.email,
        },
        render_context={
            "name": user_account.user_alias,
            "ip_address": client_ip_addr,
        },
    )

    return response
