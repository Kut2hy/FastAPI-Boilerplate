"""Pydantic models for the registration flow."""

from secrets import compare_digest
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.common.enums.country_code import CountryCodeEnum
from app.common.pydantic_classes.model import InputModel
from app.common.pydantic_classes.types.email import (
    Email,
)
from app.common.pydantic_classes.types.password import (
    RawPassword,
)
from app.common.pydantic_classes.types.phone import PhoneNumber
from app.common.pydantic_classes.types.string import (
    OptionalShortString,
    ShortString,
    String,
)
from app.common.pydantic_classes.types.zipcode import (
    PostalCode,
)


class RedisStateMixin(BaseModel):
    """Mixin class for models representing the state stored in Redis during the registration flow."""

    model_config = ConfigDict(
        extra="allow",  # To support back/forward actions in browser.
        frozen=True,
    )


# ======================================================================================================================
# Initial Registration Models
# ======================================================================================================================
class BaseEmail(BaseModel):
    email: Email
    """The email address associated with the newly created account."""


class InputEmail(InputModel, BaseEmail):
    """Pydantic model for the input email form during registration."""


class AfterCreationState(RedisStateMixin, BaseEmail):
    """Pydantic model for the state after email submission."""


# ======================================================================================================================
# Email After Click-Through Models
# ======================================================================================================================
class BaseClickThrough(BaseModel):
    """Base model for the click-through state after email submission."""

    valid: Literal["true"]
    """Indicates whether the registration token is valid."""


# NOTE: No input model as input is clicking on url token bearing link in email.


class AfterClickThroughState(AfterCreationState, BaseClickThrough):
    """Pydantic model for the state after clicking through the email link."""


# ======================================================================================================================
# Alias Submission Models
# ======================================================================================================================
class BaseAlias(BaseModel):
    """Base model for the alias submission state."""

    alias: ShortString
    """The alias (username) chosen by the user during registration."""


class InputAlias(InputModel, BaseAlias):
    """Pydantic model for the input alias form during registration."""


class AfterAliasState(AfterClickThroughState, BaseAlias):
    """Pydantic model for the state after alias submission."""


# ======================================================================================================================
# Account Information Submission Models
# ======================================================================================================================
class BaseAccountInfo(BaseModel):
    """Base model for the account information submission state."""

    first_name: ShortString
    """The first name of the user."""

    middle_name: OptionalShortString = None
    """The middle name of the user."""

    last_name: ShortString
    """The last name of the user."""

    titles_before: OptionalShortString = None
    """The titles before the name of the user."""

    titles_after: OptionalShortString = None
    """The titles after the name of the user."""

    phone_number: PhoneNumber
    """The phone number of the user."""

    street: String
    """The street address of the user."""

    city: ShortString
    """The city of the user."""

    postal_code: PostalCode
    """The postal code of the user."""

    country: CountryCodeEnum
    """The country of the user."""


class InputAccountInfo(InputModel, BaseAccountInfo):
    """Pydantic model for the input account information form during registration."""


class AfterAccountInfoState(AfterAliasState, BaseAccountInfo):
    """Pydantic model for the state after account information submission."""


# ======================================================================================================================
# Password Submission Models
# ======================================================================================================================
class BasePassword(BaseModel):
    """Base model for the password submission state."""

    password: RawPassword
    """The password chosen by the user during registration."""

    confirm_password: RawPassword
    """The confirmation of the password chosen by the user during registration."""

    @model_validator(mode="before")
    @classmethod
    def validate_passwords_match(cls, values: dict) -> dict:
        """Validate that the password and confirm_password fields match.

        Args:
            values (dict): The input values to validate.

        Returns:
            dict: The validated values if the passwords match.

        Raises:
            ValueError: If the password and confirm_password fields do not match.

        """
        password = values.get("password")
        confirm_password = values.get("confirm_password")

        if password is None or confirm_password is None:
            raise ValueError("Both password and confirm_password must be provided.")

        if not compare_digest(password, confirm_password):
            raise ValueError("Passwords do not match.")

        return values


class InputPassword(InputModel, BasePassword):
    """Pydantic model for the input password form during registration."""
