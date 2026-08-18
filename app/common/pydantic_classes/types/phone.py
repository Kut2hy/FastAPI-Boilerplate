"""Pydantic phone number type definition."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.regexp import PHONE_NUMBER_REGEXP


def nullish_phone_number_to_none(value: str | None) -> str | None:
    """Convert nullish phone number values to None.

    Args:
        value (str | None): The input phone number value.

    Returns:
        str | None: The input phone number value or None if it is nullish.

    """
    return None if value in NULLISH_STRINGS else value


PhoneNumber = Annotated[
    str,
    BeforeValidator(nullish_phone_number_to_none),
    Field(
        description="A phone number string.",
        pattern=PHONE_NUMBER_REGEXP,
    ),
]
"""Phone number type for Pydantic models. Must match the required phone number pattern."""
