"""Pydantic country code type definition."""

from typing import Annotated

from pydantic import BeforeValidator, Field, StringConstraints

from app.common.enums.country_code import CountryCodeEnum
from app.common.pydantic_classes.types.config import NULLISH_STRINGS

COUNTRY_CODE_MAX_LENGTH = 2
"""Maximum length for a country code type."""


def nullish_country_code_to_none(value: str | None) -> str | None:
    """Convert nullish country code values to None.

    Args:
        value (str | None): The input country code value.

    Returns:
        str | None: The input country code value or None if it is nullish.

    """
    if value is None:
        return None

    value = value.strip()

    return None if value in NULLISH_STRINGS else value.upper()


CountryCode = Annotated[
    CountryCodeEnum,
    BeforeValidator(nullish_country_code_to_none),
    StringConstraints(
        min_length=COUNTRY_CODE_MAX_LENGTH,
        max_length=COUNTRY_CODE_MAX_LENGTH,
    ),
    Field(
        description="A country code string. Must be a valid ISO 3166-1 alpha-2 country code.",
    ),
]
"""Country code type for Pydantic models."""
