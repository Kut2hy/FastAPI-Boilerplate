"""Pydantic generic string types definition."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.common.pydantic_classes.types.config import NULLISH_STRINGS, STANDARD_VARCHAR_LENGTH

SHORT_STRING_MAX_LENGTH = 50
"""Maximum length for a short string type."""

STRING_MAX_LENGTH = STANDARD_VARCHAR_LENGTH
"""Maximum length for a standard string type."""

LONG_STRING_MAX_LENGTH = 10000
"""Maximum length for a long string type."""


def nullish_string_to_none(value: str | None) -> str | None:
    """Convert nullish values to None.

    Args:
        value (str | None): The input string value.

    Returns:
        str | None: The input string value or None if it is nullish.

    """
    return None if value in NULLISH_STRINGS else value


ShortString = Annotated[
    str,
    Field(
        description="A short string.",
        min_length=1,
        max_length=SHORT_STRING_MAX_LENGTH,
    ),
]
"""Generic short string type for Pydantic models."""


OptionalShortString = Annotated[
    ShortString | None,
    BeforeValidator(nullish_string_to_none),
    Field(description="An optional short string."),
]
"""Generic optional short string type for Pydantic models."""


String = Annotated[
    str,
    Field(
        description="A string.",
        min_length=1,
        max_length=STRING_MAX_LENGTH,
    ),
]
"""Generic string type for Pydantic models."""


OptionalString = Annotated[
    String | None,
    BeforeValidator(nullish_string_to_none),
    Field(description="An optional string."),
]
"""Generic optional string type for Pydantic models."""


LongString = Annotated[
    str,
    Field(
        description="A long string.",
        min_length=1,
        max_length=LONG_STRING_MAX_LENGTH,
    ),
]
"""Generic long string type for Pydantic models."""


OptionalLongString = Annotated[
    LongString | None,
    BeforeValidator(nullish_string_to_none),
    Field(description="An optional long string."),
]
"""Generic optional long string type for Pydantic models."""
