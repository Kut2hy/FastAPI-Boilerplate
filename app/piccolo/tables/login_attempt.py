"""Piccolo table definition for storing login attempts."""

from piccolo.columns import (
    Boolean,
    ForeignKey,
    Integer,
    OnDelete,
    OnUpdate,
    Varchar,
)
from piccolo.columns.reference import LazyTableReference
from piccolo.table import Table

from app.piccolo.mixins import CreatedAtMixin, PKMixin


class LoginAttempt(CreatedAtMixin, PKMixin, Table):
    """SQL table for storing login attempts."""

    user_id = ForeignKey(
        references=LazyTableReference("UserAccount", module_path="app.piccolo.tables.user_account"),
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.cascade,
        null=True,
    )
    """User ID associated with the token. This is a foreign key to the User Account table."""

    user_email = Varchar(length=255, null=False, index=True)
    """
    Email address used in the login attempt. This is not a foreign key to the User table because we want
    to log attempts even for non-existent users."""

    user_ip_address = Varchar(length=45, null=False)
    """IP address from which the login attempt was made. Supports both IPv4 and IPv6."""

    was_successful = Boolean(null=False, index=True)
    """Indicates whether the login attempt was successful or not."""

    response_code = Integer(null=False)
    """
    HTTP response code returned for the login attempt.
    302, 303, 307 codes indicate a successful login, any other code indicates a failed login attempt.
    """

    reason = Varchar(length=255, null=True)
    """
    Reason for the login attempt result. This provides additional context for failed login attempts,
    such as "Invalid credentials", "User is blocked", etc.
    """
