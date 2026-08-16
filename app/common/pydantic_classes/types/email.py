"""Pydantic email type definition."""

from re import compile as re_compile
from typing import Annotated

from pydantic import BeforeValidator, Field, Secret

from app.common.pydantic_classes.types.config import STANDARD_VARCHAR_LENGTH, NULLISH_STRINGS
from app.common.regexp import EMAIL_REGEXP

_EMAIL_REGEXP = re_compile(EMAIL_REGEXP)
"""Pre-compiled regex pattern for email validation."""


def prepare_email_value(value: str) -> str:
    """Value unification function for email.

    This function trims whitespace, converts the value to lowercase
    and raises an error for nullish strings (for non-filled values in forms).

    Args:
        value (str): The input value to prepare.

    Returns:
        str: The prepared value.

    Raises:
        ValueError: If the input value is not a string or if it is a nullish string.

    """

    if isinstance(value, str):
        value = value.strip().lower()

        if value in NULLISH_STRINGS:
            raise ValueError("Value must not be nullish")

        return value

    raise ValueError(f"Value must be a string, got {type(value)}")


Email = Secret[
    Annotated[
        str,
        BeforeValidator(prepare_email_value),
        Field(
            description="An email string in Secret format.",
            pattern=_EMAIL_REGEXP,
            max_length=STANDARD_VARCHAR_LENGTH,
        ),
    ]
]
"""
Email type for Pydantic models.
Uses Pydantic's Secret to ensure that the email is treated as sensitive information.
Regexp validation based on https://html.spec.whatwg.org/multipage/input.html#email-state-(type=email).
"""
