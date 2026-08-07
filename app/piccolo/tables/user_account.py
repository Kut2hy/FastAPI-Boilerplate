"""Definitions of the Account table and Pydantic DB facing models."""

from piccolo.columns import (
    Array,
    Boolean,
    Secret,
    Varchar,
)
from piccolo.constraints import Unique
from piccolo.table import Table

from app.piccolo.mixins import (
    CreatedAtMixin,
    CreatedByMixin,
    PKMixin,
    UpdatedAtMixin,
    UpdatedByMixin,
    WasReviewedMixin,
)

STRING_MAX_LENGTH = 255
"""Maximum length for string columns."""

SHORT_STRING_MAX_LENGTH = 50
"""Maximum length for short string columns."""

POSTAL_CODE_MAX_LENGTH = 5
"""Maximum length for postal code columns."""

COUNTRY_CODE_MAX_LENGTH = 2
"""Maximum length for country code columns."""


class UserAccount(
    PKMixin,
    CreatedAtMixin,
    CreatedByMixin,
    UpdatedAtMixin,
    UpdatedByMixin,
    WasReviewedMixin,
    Table,
):
    """SQL table for storing user accounts."""

    email = Secret(length=STRING_MAX_LENGTH, unique=True, null=False)
    """Unique email address for the user account."""

    user_alias = Varchar(length=SHORT_STRING_MAX_LENGTH, unique=True, null=False)
    """Unique, public facing alias for the user account."""

    receive_notifications = Boolean(default=True, null=False)
    """Indicates whether the user account should receive notifications via email."""

    password_hash = Secret(length=STRING_MAX_LENGTH, null=False)
    """Hashed password for the user account."""

    granted_roles = Array(base_column=Varchar(length=SHORT_STRING_MAX_LENGTH), null=False, default=list)
    """List of roles granted to the user account."""

    is_locked = Boolean(default=False, null=False)
    """Indicates whether the user account is locked."""

    was_email_verified = Boolean(default=False, null=False)
    """Indicates whether the email address has been verified."""

    first_name = Varchar(length=SHORT_STRING_MAX_LENGTH, null=False)
    """First name of the user."""

    middle_name = Varchar(length=SHORT_STRING_MAX_LENGTH, null=True, default=None)
    """Middle name of the user."""

    last_name = Varchar(length=SHORT_STRING_MAX_LENGTH, null=False)
    """Last name of the user."""

    titles_before = Varchar(length=SHORT_STRING_MAX_LENGTH, null=True, default=None)
    """Titles before the name of the user."""

    titles_after = Varchar(length=SHORT_STRING_MAX_LENGTH, null=True, default=None)
    """Titles after the name of the user."""

    phone_number = Varchar(length=SHORT_STRING_MAX_LENGTH, null=True, default=None)
    """Phone number of the user."""

    street = Varchar(length=STRING_MAX_LENGTH, null=False)
    """Street address of the user."""

    city = Varchar(length=SHORT_STRING_MAX_LENGTH, null=False)
    """City of the user."""

    postal_code = Varchar(length=POSTAL_CODE_MAX_LENGTH, null=False)
    """Postal code of the user."""

    country = Varchar(length=COUNTRY_CODE_MAX_LENGTH, null=False)
    """Country of the user."""

    # ==================================================================================================================
    # Constraints
    # ==================================================================================================================

    unique_email_user_alias = Unique(columns=["email", "user_alias"])
    """Unique constraint to ensure that the combination of email and user_alias is unique across all records."""
