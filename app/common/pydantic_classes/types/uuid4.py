"""Pydantic uuid type definition."""

from typing import Annotated
from uuid import UUID as _UUID

from pydantic import UUID4 as _UUID4
from pydantic import BeforeValidator, Field

NULLISH_STRINGS = ("", "null", "undefined")
"""Strings that should be treated as None when validating UUIDs."""


def str2uuid(value: str | _UUID | None) -> _UUID | None:
    """Pydantic validator to convert a string to a UUID.

    This is useful for form inputs where UUIDs are often represented as strings.

    Args:
        value (str | UUID | None): The value to convert to a UUID.

    Returns:
        UUID | None: The converted UUID or None if the input is None or a nullish string.

    Raises:
        ValueError: If the value is not a string, UUID, or None.

    """

    if value is None:
        return None

    if isinstance(value, _UUID):
        return value

    if isinstance(value, str):
        value = value.strip()

        if value is None or value in NULLISH_STRINGS:
            return None

        return _UUID(value)

    raise ValueError(f"Value must be a string or UUID, got {type(value)}")


UUID4 = Annotated[
    _UUID4,
    BeforeValidator(str2uuid),
    Field(
        description="A UUID4 type with internal str to UUID conversion.",
    ),
]
"""UUID4 type for Pydantic models."""


OptionalUUID4 = Annotated[
    _UUID4 | None,
    BeforeValidator(str2uuid),
    Field(
        description="An optional UUID4 type with internal str to UUID conversion.",
        default=None,
    ),
]
"""Optional UUID4 type where nullish strings ("", "null", "undefined") are coerced to None."""
