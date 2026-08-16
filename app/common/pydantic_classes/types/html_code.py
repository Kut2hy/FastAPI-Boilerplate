"""Pydantic type for HTML code."""

from enum import IntEnum
from typing import Annotated, cast

from fastapi import status
from pydantic import Field

# NOTE: This is a workaround to make Pylance happy, as it does not like a dynamically created Enum.
HTMLResponseCodeEnum = cast(
    "type[IntEnum]",
    IntEnum(
        "HTMLResponseCodeEnum",
        {k: getattr(status, k) for k in status.__all__ if k.startswith("HTTP_")},
    ),
)
"""Enum for HTML response codes, generated from http.HTTPStatus."""


HTMLResponseCode = Annotated[
    HTMLResponseCodeEnum,
    Field(
        description="An HTML code integer.",
    ),
]
"""HTML response code type for Pydantic models."""
