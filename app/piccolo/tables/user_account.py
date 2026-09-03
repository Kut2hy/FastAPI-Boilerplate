"""Definitions of the Account table and Pydantic DB facing models."""

from typing import overload
from uuid import UUID, uuid7

from piccolo.columns import (
    Array,
    Boolean,
    Secret,
    Varchar,
)
from piccolo.constraints import Unique
from piccolo.table import Table

from app.common.middleware.server_timings import capture_duration
from app.common.pydantic_classes.types.country import CountryCode
from app.common.pydantic_classes.types.email import Email
from app.common.pydantic_classes.types.password import RawPassword
from app.common.pydantic_classes.types.string import ShortString, String
from app.common.pydantic_classes.types.zipcode import PostalCode
from app.core.password import hash_password
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


@capture_duration()
async def create_account(
    email: Email,
    alias: ShortString,
    password: RawPassword,
    was_email_verified: bool,
    first_name: ShortString,
    middle_name: ShortString | None,
    last_name: ShortString,
    titles_before: ShortString | None,
    titles_after: ShortString | None,
    phone_number: ShortString | None,
    street: String,
    city: ShortString,
    postal_code: PostalCode,
    country: CountryCode,
) -> UserAccount | None:
    """Create a new user account.

    Args:
        email (Email): The email address for the new user account.
        alias (ShortString): The public facing alias for the new user account.
        password (RawPassword): The raw password for the new user account.
        was_email_verified (bool): Indicates whether the email address has been verified.
        first_name (ShortString): The first name of the user.
        middle_name (ShortString | None): The middle name of the user.
        last_name (ShortString): The last name of the user.
        titles_before (ShortString | None): Titles before the name of the user.
        titles_after (ShortString | None): Titles after the name of the user.
        phone_number (ShortString | None): The phone number of the user.
        street (String): The street address of the user.
        city (ShortString): The city of the user.
        postal_code (PostalCode): The postal code of the user.
        country (CountryCode): The country of the user.

    Returns:
        UserAccount | None: The newly created user account, or None if creation failed.

    """
    async with UserAccount._meta.db.transaction():  # noqa: SLF001
        if await UserAccount.exists().where(
            (UserAccount.email == email.get_secret_value()) | (UserAccount.user_alias == alias)
        ):
            return None

        new_account_id = uuid7()  # Generate a new UUID for the user account
        new_account = UserAccount(
            {
                UserAccount.id: new_account_id,
                UserAccount.email: email.get_secret_value(),
                UserAccount.user_alias: alias,
                UserAccount.password_hash: hash_password(password.get_secret_value()),
                UserAccount.was_email_verified: was_email_verified,
                UserAccount.first_name: first_name,
                UserAccount.middle_name: middle_name,
                UserAccount.titles_before: titles_before,
                UserAccount.titles_after: titles_after,
                UserAccount.phone_number: phone_number,
                UserAccount.last_name: last_name,
                UserAccount.street: street,
                UserAccount.city: city,
                UserAccount.postal_code: postal_code,
                UserAccount.country: country,
                UserAccount.created_by: new_account_id,  # Assuming the user is creating their own account
                UserAccount.updated_by: new_account_id,  # Assuming the user is creating their own account
            }
        )

        # Save the new user account to the database
        result = await new_account.save().returning(UserAccount.id)

        if not result or result[0]["id"] != new_account_id:
            return None

    return new_account


@overload
async def get_user(identifier: str) -> UserAccount | None: ...
@overload
async def get_user(identifier: UUID) -> UserAccount | None: ...


@capture_duration()
async def get_user(identifier: str | UUID) -> UserAccount | None:
    """Retrieve a user account by email or UUID.

    Args:
        identifier (str | UUID): The email or UUID of the user account.

    Returns:
        UserAccount | None: The user account if found, otherwise None.

    """
    user = UserAccount.objects()

    if isinstance(identifier, str):
        user = user.where(UserAccount.email == identifier)

    elif isinstance(identifier, UUID):
        user = user.where(UserAccount.id == identifier)

    else:
        raise TypeError("Identifier must be a string email or a UUID.")

    return await user.first()


@overload
async def account_exists(email: str, alias: str) -> tuple[bool, bool]: ...
@overload
async def account_exists(email: str, alias: None) -> tuple[bool, None]: ...
@overload
async def account_exists(email: None, alias: str) -> tuple[None, bool]: ...


@capture_duration()
async def account_exists(email: str | None = None, alias: str | None = None) -> tuple[bool | None, bool | None]:
    """Check if a user account exists with the given email or alias.

    Args:
        email (str | None): The email address to check for existence.
        alias (str | None): The alias to check for existence.

    Returns:
        tuple[bool | None, bool | None]: A tuple indicating the existence of the email and alias respectively.
            True if exists, False if not, None if not checked.

    """
    if email is None and alias is None:
        raise ValueError("At least one of email or alias must be provided.")

    email_exists = None
    alias_exists = None

    async with UserAccount._meta.db.transaction():  # noqa: SLF001
        if email:
            email_exists = await UserAccount.exists().where(UserAccount.email == email)

        if alias:
            alias_exists = await UserAccount.exists().where(UserAccount.user_alias == alias)

    return email_exists, alias_exists


@capture_duration()
async def change_password(email: Email, new_password: RawPassword) -> bool:
    """Change the password for a user account.

    Args:
        email (Email): The email of the user account.
        new_password (RawPassword): The new raw password to set.

    Returns:
        bool: True if the password was changed successfully, False otherwise.

    """
    hashed_password = hash_password(new_password.get_secret_value())

    async with UserAccount._meta.db.transaction() as transaction:  # noqa: SLF001
        user_account = await UserAccount.objects().where(UserAccount.email == email.get_secret_value()).first()

        if not user_account:
            return False

        user_account.password_hash = hashed_password
        user_account.updated_by = user_account.id  # Assuming the user is changing their own password

        result = await user_account.save().returning(UserAccount.id)

        if not bool(result) or len(result) != 1:
            transaction.rollback()
            return False

        return True
