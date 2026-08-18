"""Piccolo table definition for storing login attempts."""

from piccolo.columns import (
    Boolean,
    Integer,
    Varchar,
)
from piccolo.table import Table

from app.piccolo.mixins import CreatedAtMixin, PKMixin


class LoginAttempt(CreatedAtMixin, PKMixin, Table):
    """SQL table for storing login attempts for auditing purposes."""

    user_email = Varchar(length=255, null=False, index=True)
    """
    Email address used in the login attempt. This is not a foreign key to the User table because we want
    to log attempts even for non-existent users."""

    user_ip_address = Varchar(length=45, null=False)
    """IP address from which the login attempt was made. Supports both IPv4 and IPv6."""

    was_successful = Boolean(null=False, index=True)
    """Indicates whether the login attempt was successful or not."""

    status_code = Integer(null=False)
    """
    HTTP response code returned for the login attempt.
    302, 303, 307 codes indicate a successful login, any other code indicates a failed login attempt.
    """


async def add_login_attempt(
    user_email: str,
    user_ip_address: str,
    status_code: int = 200,
) -> None:
    """Add a login attempt to the database.

    Args:
        user_email (str): The email address used in the login attempt.
        user_ip_address (str): The IP address from which the login attempt was made.
        status_code (int): HTTP response code returned for the login attempt.

    """
    await LoginAttempt(
        {
            LoginAttempt.user_email: user_email,
            LoginAttempt.user_ip_address: user_ip_address,
            LoginAttempt.was_successful: str(status_code).startswith(("2", "3")),  # 2xx and 3xx codes indicate success
            LoginAttempt.status_code: status_code,
        }
    ).save()
