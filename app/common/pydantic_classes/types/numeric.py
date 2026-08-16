"""Pydantic generic numeric types definition."""

from typing import Annotated

from pydantic import BeforeValidator, Field

from app.common.pydantic_classes.types.config import INTEGER_MAX_VALUE, NULLISH_STRINGS


def nullish_to_none(value: int | str | None) -> int | str | None:
    """Convert nullish values to None.

    Args:
        value (int | str | None): The input value.

    Returns:
        int | str | None: The input value or None if it is nullish.

    """
    return None if value in NULLISH_STRINGS else value


PositiveInt = Annotated[
    int,
    Field(
        description="A positive integer.",
        ge=0,
        le=INTEGER_MAX_VALUE,
    ),
]
"""Generic positive integer type for Pydantic models."""


OptionalPositiveInt = Annotated[
    PositiveInt | None,
    BeforeValidator(nullish_to_none),
    Field(description="An optional positive integer."),
]
"""Generic optional positive integer type for Pydantic models."""
