"""Pydantic postal code type definition."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.regexp import POSTAL_CODE_REGEXP


def nullish_postal_code_to_none(value: str | None) -> str | None:
    """Convert nullish postal code values to None.

    Args:
        value (str | None): The input postal code value.

    Returns:
        str | None: The input postal code value or None if it is nullish.

    """
    return None if value in NULLISH_STRINGS else value


PostalCode = Annotated[
    str,
    BeforeValidator(nullish_postal_code_to_none),
    Field(
        description="A postal code string.",
        pattern=POSTAL_CODE_REGEXP,
    ),
]
"""Postal code type for Pydantic models. Must match the required postal code pattern."""
